import argparse
import asyncio
import statistics
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.logmind_eval import (  # noqa: E402
    REPORT_QUALITY_WEIGHTS,
    evaluate_logmind_report_case,
    load_logmind_report_eval_cases,
)

LIVE_REPORT_SYSTEM_PROMPT = """\
你是 LogMind 智能日志分析与运维排障 Agent。
请根据用户提供的日志或故障现象生成诊断报告。

当前后端规则分类器给出的初步故障类型是：{fault_type}。
该分类只作为辅助判断，不是最终结论；如果日志证据与分类不一致，请基于日志证据说明原因。

以下是从 LogMind 运维知识库中检索到的参考片段：
{knowledge_context}

请优先结合用户日志和参考知识进行分析。参考知识只能作为辅助依据，不能替代日志证据；如果参考知识与日志不匹配，请明确说明。

报告必须严格使用以下 Markdown 结构：
## 1. 问题概述
- 故障类型：
- 严重等级：
- 影响组件：
- 简要说明：

## 2. 关键信息提取
- 至少保留一个原始错误短语、错误码、端口号或异常类名，不要只做同义改写
## 3. 可能原因分析
- 给出可能原因，必须和日志证据对应；使用的关键错误短语、错误码、端口号或异常类名必须保留原文，不要改写成泛化描述
## 4. 建议排查步骤
- 给出可执行的排查步骤，并在步骤中保留对应的关键错误短语、错误码、端口号或异常类名
## 5. 修复建议
- 给出修复建议，并说明建议针对的是哪个关键错误短语、错误码、端口号或异常类名
## 6. 后续预防建议
## 7. 参考知识
- 有命中时，每一项必须以本次提供的知识标题开头，格式为 `- 知识标题：简短说明`
- 禁止使用“命中参考知识”“参考要点”“相关资料”等泛化标题代替真实知识标题
- 没有命中时填写 `- 未命中参考知识`

除“问题概述”里的固定字段外，其余章节正文必须使用 `- ` 开头的无序列表。
不要编造命令结果，不要输出敏感信息。没有参考知识时，在参考知识部分说明未命中。
"""


def _format_knowledge_context(knowledge_refs: list[Any]) -> str:
    if not knowledge_refs:
        return "未检索到匹配的知识库片段，请主要基于用户日志进行分析。"

    sections = []
    for index, ref in enumerate(knowledge_refs, start=1):
        sections.append(
            f"[{index}] {ref.title}\n"
            f"来源：{ref.source or '本地知识库'}\n"
            f"摘要：\n{ref.snippet or ''}"
        )

    return "\n\n".join(sections)


def _extract_token_usage(response: Any) -> dict[str, int]:
    usage_metadata = getattr(response, "usage_metadata", None)
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

    if isinstance(usage_metadata, dict):
        input_tokens = _metadata_int(usage_metadata.get("input_tokens"))
        output_tokens = _metadata_int(usage_metadata.get("output_tokens"))
        total_tokens = _metadata_int(usage_metadata.get("total_tokens"))

    response_metadata = getattr(response, "response_metadata", None)
    if isinstance(response_metadata, dict):
        token_usage = response_metadata.get("token_usage") or response_metadata.get("usage")
        if isinstance(token_usage, dict):
            input_tokens = (
                input_tokens
                or _metadata_int(token_usage.get("input_tokens"))
                or _metadata_int(token_usage.get("prompt_tokens"))
            )
            output_tokens = (
                output_tokens
                or _metadata_int(token_usage.get("output_tokens"))
                or _metadata_int(token_usage.get("completion_tokens"))
            )
            total_tokens = total_tokens or _metadata_int(token_usage.get("total_tokens"))

    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens

    usage: dict[str, int] = {}
    if input_tokens is not None:
        usage["input_tokens"] = input_tokens
    if output_tokens is not None:
        usage["output_tokens"] = output_tokens
    if total_tokens is not None:
        usage["total_tokens"] = total_tokens

    return usage


def _metadata_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _estimate_cost_usd(
    token_usage: dict[str, int],
    *,
    input_price_per_1m: float,
    output_price_per_1m: float,
) -> float | None:
    if input_price_per_1m <= 0 and output_price_per_1m <= 0:
        return None

    input_tokens = token_usage.get("input_tokens", 0)
    output_tokens = token_usage.get("output_tokens", 0)
    cost = (input_tokens / 1_000_000 * input_price_per_1m) + (
        output_tokens / 1_000_000 * output_price_per_1m
    )
    return round(cost, 8)


def _p50(values: list[float]) -> float:
    if not values:
        return 0.0

    return statistics.median(values)


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]

    return statistics.quantiles(values, n=20, method="inclusive")[18]


async def _run_live_eval(args: argparse.Namespace) -> int:
    from langchain_core.messages import HumanMessage, SystemMessage

    from agents.logmind_classifier import classify_fault_type
    from core import get_model, settings
    from core.knowledge_base import retrieve_knowledge

    cases = load_logmind_report_eval_cases(args.report_cases)[: args.sample_size]
    model_name = args.model or settings.DEFAULT_MODEL
    model = get_model(model_name)

    results = []
    latencies_ms: list[float] = []
    model_latencies_ms: list[float] = []
    token_totals: list[int] = []
    estimated_costs: list[float] = []
    classification_passed = 0

    for case in cases:
        started_at = perf_counter()
        classified_fault_type = classify_fault_type(case.input_summary)
        knowledge_refs = retrieve_knowledge(
            case.input_summary,
            fault_type=classified_fault_type,
            k=3,
        )
        model_started_at = perf_counter()
        response = await model.ainvoke(
            [
                SystemMessage(
                    content=LIVE_REPORT_SYSTEM_PROMPT.format(
                        fault_type=classified_fault_type.value,
                        knowledge_context=_format_knowledge_context(knowledge_refs),
                    )
                ),
                HumanMessage(content=case.input_summary),
            ]
        )
        model_latency_ms = (perf_counter() - model_started_at) * 1000
        total_latency_ms = (perf_counter() - started_at) * 1000
        model_latencies_ms.append(model_latency_ms)
        latencies_ms.append(total_latency_ms)

        token_usage = _extract_token_usage(response)
        total_tokens = token_usage.get("total_tokens")
        if total_tokens is not None:
            token_totals.append(total_tokens)
        estimated_cost_usd = _estimate_cost_usd(
            token_usage,
            input_price_per_1m=settings.LOGMIND_INPUT_TOKEN_PRICE_PER_1M_USD,
            output_price_per_1m=settings.LOGMIND_OUTPUT_TOKEN_PRICE_PER_1M_USD,
        )
        if estimated_cost_usd is not None:
            estimated_costs.append(estimated_cost_usd)

        evaluated_case = case.model_copy(
            update={
                "report_markdown": str(response.content),
                "knowledge_refs": knowledge_refs,
            }
        )
        result = evaluate_logmind_report_case(evaluated_case)
        results.append(result)
        classification_matched = classified_fault_type == case.expected_fault_type
        classification_passed += int(classification_matched)

        status = "PASS" if result.passed else "FAIL"
        print(
            f"[{status}] {case.id}: "
            f"quality_score={result.quality_score}, "
            f"classified_fault_type={classified_fault_type.value}, "
            f"classification_match={classification_matched}, "
            f"knowledge_hits={len(knowledge_refs)}, "
            f"total_latency_ms={total_latency_ms:.0f}, "
            f"model_latency_ms={model_latency_ms:.0f}, "
            f"tokens={total_tokens if total_tokens is not None else 'unknown'}, "
            f"cost_usd={estimated_cost_usd if estimated_cost_usd is not None else 'unknown'}"
        )
        for issue in result.issues:
            print(f"  - {issue}")

    total = len(results)
    passed = sum(result.passed for result in results)
    average_quality = (
        sum(result.quality_score for result in results) / total if total else 0.0
    )
    average_latency = sum(latencies_ms) / total if total else 0.0
    average_tokens = sum(token_totals) / len(token_totals) if token_totals else 0.0
    average_cost = sum(estimated_costs) / len(estimated_costs) if estimated_costs else 0.0
    structure_complete_rate = _metric_rate(
        results,
        lambda result: result.quality_breakdown.get("sections", 0)
        == REPORT_QUALITY_WEIGHTS["sections"],
    )
    evidence_coverage_rate = _metric_rate(
        results,
        lambda result: result.quality_breakdown.get("evidence", 0)
        == REPORT_QUALITY_WEIGHTS["evidence"],
    )
    reference_accuracy_rate = _metric_rate(
        results,
        lambda result: result.reference_accuracy_passed,
    )
    fact_consistency_rate = _metric_rate(
        results,
        lambda result: result.fact_consistency_passed,
    )

    print(
        "Live LogMind report eval: "
        f"{passed}/{total} passed, "
        f"classification_accuracy={classification_passed / total if total else 0.0:.1%}, "
        f"average_quality_score={average_quality:.1f}, "
        f"structure_complete_rate={structure_complete_rate:.1%}, "
        f"evidence_coverage_rate={evidence_coverage_rate:.1%}, "
        f"reference_accuracy={reference_accuracy_rate:.1%}, "
        f"fact_consistency={fact_consistency_rate:.1%}, "
        f"average_total_latency_ms={average_latency:.0f}, "
        f"p50_total_latency_ms={_p50(latencies_ms):.0f}, "
        f"p95_total_latency_ms={_p95(latencies_ms):.0f}, "
        f"average_model_latency_ms={sum(model_latencies_ms) / total if total else 0.0:.0f}, "
        f"average_total_tokens={average_tokens:.0f}, "
        f"average_estimated_cost_usd={average_cost:.8f}"
    )

    return 0 if passed == total else 1


def _metric_rate(results: list[Any], predicate) -> float:
    total = len(results)
    if not total:
        return 0.0

    return sum(1 for result in results if predicate(result)) / total


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run an optional live-model sample evaluation for LogMind reports."
    )
    parser.add_argument(
        "--report-cases",
        type=Path,
        default=ROOT_DIR / "tests" / "fixtures" / "logmind_report_eval_cases.json",
        help="Path to LogMind report eval cases JSON.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=5,
        help="Number of report cases to sample.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model name. Defaults to settings.DEFAULT_MODEL when live mode is enabled.",
    )
    parser.add_argument(
        "--run-live-model",
        action="store_true",
        help="Actually call the configured LLM. Without this flag the script only prints a dry run.",
    )
    args = parser.parse_args()

    cases = load_logmind_report_eval_cases(args.report_cases)
    sample_size = min(args.sample_size, len(cases))

    if not args.run_live_model:
        print("Dry run only. Pass --run-live-model to call the configured LLM.")
        print(
            f"Would evaluate {sample_size}/{len(cases)} report cases "
            f"with model={args.model or '<settings.DEFAULT_MODEL>'} and print "
            "quality, p50/p95 latency, tokens and estimated cost."
        )
        return 0

    return asyncio.run(_run_live_eval(args))


if __name__ == "__main__":
    raise SystemExit(main())
