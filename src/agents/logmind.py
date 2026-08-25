import logging
from textwrap import dedent
from time import perf_counter

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.func import entrypoint

from agents.logmind_classifier import classify_fault_type, is_diagnostic_request
from core import get_model, settings
from core.diagnosis_parser import parse_diagnosis_markdown
from core.diagnosis_store import list_similar_diagnosis_records, save_diagnosis_record
from core.knowledge_base import retrieve_knowledge
from core.logmind_eval import (
    LogMindReportEvalCase,
    evaluate_knowledge_reference_accuracy,
    evaluate_logmind_report_case,
)
from core.logmind_tooling import LogMindToolRun, run_async_agent_tool, run_sync_agent_tool
from core.sensitive_data import sanitize_sensitive_text
from schema import (
    AgentTraceStep,
    DiagnosisQualityEvaluation,
    FaultType,
    KnowledgeRef,
    Severity,
    SimilarIncidentRef,
)

logger = logging.getLogger(__name__)

DIAGNOSIS_OUTPUT_CONTRACT = """\
诊断报告必须严格使用以下 Markdown 结构，不要改标题名称，不要合并章节，不要省略章节。
除“问题概述”里的固定字段外，其余章节正文必须使用 `- ` 开头的无序列表。

## 1. 问题概述
- 故障类型：使用当前证据判断出的故障类型
- 严重等级：只能填写 低 / 中 / 高 / 严重
- 影响组件：填写具体组件；无法判断时填写 未知
- 简要说明：用一句话概括问题

## 2. 关键信息提取
- 从用户日志或异常堆栈中提取关键证据，至少保留一个原始错误短语、错误码、端口号或异常类名，不要只做同义改写

## 3. 可能原因分析
- 给出可能原因，必须和日志证据对应；使用的关键错误短语、错误码、端口号或异常类名必须保留原文，不要改写成泛化描述

## 4. 建议排查步骤
- 给出可执行的排查步骤，并在步骤中保留对应的关键错误短语、错误码、端口号或异常类名

## 5. 修复建议
- 给出修复建议，并说明建议针对的是哪个关键错误短语、错误码、端口号或异常类名

## 6. 后续预防建议
- 给出预防建议

## 7. 参考知识
- 有命中时，每一项必须以本次提供的知识标题开头，格式为 `- 知识标题：简短说明`
- 禁止使用“命中参考知识”“参考要点”“相关资料”等泛化标题代替真实知识标题
- 没有命中时填写 `- 未命中参考知识`
"""


def _format_knowledge_refs(knowledge_refs: list[KnowledgeRef]) -> str:
    if not knowledge_refs:
        return "未检索到匹配的知识库片段，请主要基于用户日志和已有上下文进行分析。"

    sections = []
    for index, ref in enumerate(knowledge_refs, start=1):
        sections.append(
            f"""[{index}] {ref.title}
来源：{ref.source or "本地知识库"}
摘要：
{ref.snippet or ""}"""
        )

    return "\n\n".join(sections)


def _format_similar_incidents(similar_incidents: list[SimilarIncidentRef]) -> str:
    if not similar_incidents:
        return "未检索到相似历史诊断案例。"

    sections = []
    for index, incident in enumerate(similar_incidents, start=1):
        sections.append(
            f"""[{index}] {incident.summary}
记录 ID：{incident.record_id}
故障类型：{incident.fault_type.value}
严重等级：{incident.severity.value}
诊断时间：{incident.created_at}"""
        )

    return "\n\n".join(sections)


def _message_text(message: BaseMessage) -> str:
    return message.content if isinstance(message.content, str) else str(message.content)


def _sanitize_message(message: BaseMessage) -> BaseMessage:
    if not isinstance(message.content, str):
        return message

    sanitized_content = sanitize_sensitive_text(message.content)
    if sanitized_content == message.content:
        return message

    return message.model_copy(update={"content": sanitized_content})


def _sanitize_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
    return [_sanitize_message(message) for message in messages]


def _preview_text(text: str, limit: int = 120) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized

    return normalized[: limit - 3] + "..."


def _run_input_sanitization_tool(
    *,
    messages: list[BaseMessage],
    latest_user_message: str,
) -> LogMindToolRun[tuple[list[BaseMessage], str]]:
    return run_sync_agent_tool(
        step="input_sanitization",
        title="输入敏感信息脱敏",
        tool_name="sanitize_sensitive_text",
        call=lambda: (
            _sanitize_messages(messages),
            sanitize_sensitive_text(latest_user_message),
        ),
        success_detail="对用户输入和历史上下文进行敏感信息脱敏。",
        success_metadata=lambda value: {
            "message_count": len(value[0]),
            "latest_message_changed": value[1] != latest_user_message,
            "tool_input_summary": _preview_text(latest_user_message),
            "tool_output_summary": _preview_text(value[1]),
        },
    )


def _run_diagnostic_request_tool(query: str) -> LogMindToolRun[bool]:
    return run_sync_agent_tool(
        step="diagnostic_request_check",
        title="诊断请求识别",
        tool_name="is_diagnostic_request",
        call=lambda: is_diagnostic_request(query),
        success_detail="判断用户输入是否属于日志、异常堆栈或故障排查请求。",
        success_metadata=lambda is_diagnostic: {
            "is_diagnostic_request": is_diagnostic,
            "tool_input_summary": _preview_text(query),
            "tool_output_summary": str(is_diagnostic),
        },
    )


def _run_fault_classification_tool(query: str) -> LogMindToolRun[FaultType]:
    return run_sync_agent_tool(
        step="fault_classification",
        title="故障类型分类",
        tool_name="classify_fault_type",
        call=lambda: classify_fault_type(query),
        success_detail=lambda fault_type: f"规则分类器识别为 {fault_type.value}。",
        success_metadata=lambda fault_type: {
            "fault_type": fault_type.value,
            "tool_input_summary": _preview_text(query),
            "tool_output_summary": fault_type.value,
        },
    )


def _run_knowledge_retrieval_tool(
    query: str,
    *,
    fault_type: FaultType,
    k: int,
) -> LogMindToolRun[list[KnowledgeRef]]:
    return run_sync_agent_tool(
        step="knowledge_retrieval",
        title="知识库检索",
        tool_name="retrieve_knowledge",
        call=lambda: retrieve_knowledge(
            query,
            fault_type=fault_type,
            k=k,
        ),
        success_detail=lambda refs: f"检索到 {len(refs)} 条参考知识。",
        success_metadata=lambda refs: {
            "fault_type": fault_type.value,
            "top_k": k,
            "hit_count": len(refs),
            "tool_input_summary": _preview_text(query),
            "tool_output_summary": f"{len(refs)} knowledge refs",
        },
        fallback=[],
        failure_detail="知识库检索失败，已降级为空引用继续诊断。",
        logger=logger,
        log_message="Knowledge retrieval failed; continuing without references.",
    )


async def _run_similar_incident_retrieval_tool(
    *,
    fault_type: FaultType,
    user_id: str | None,
    thread_id: str | None,
    limit: int,
) -> LogMindToolRun[list[SimilarIncidentRef]]:
    return await run_async_agent_tool(
        step="similar_incident_retrieval",
        title="相似历史案例检索",
        tool_name="list_similar_diagnosis_records",
        call=lambda: list_similar_diagnosis_records(
            fault_type=fault_type,
            user_id=user_id,
            exclude_thread_id=thread_id,
            limit=limit,
        ),
        success_detail=lambda incidents: f"检索到 {len(incidents)} 条相似历史诊断案例。",
        success_metadata=lambda incidents: {
            "fault_type": fault_type.value,
            "hit_count": len(incidents),
            "tool_input_summary": f"fault_type={fault_type.value}, limit={limit}",
            "tool_output_summary": f"{len(incidents)} similar incidents",
        },
        fallback=[],
        failure_detail="相似历史案例检索失败，已降级为空历史案例继续诊断。",
        logger=logger,
        log_message="Similar incident retrieval failed; continuing without history.",
    )


def _retrieve_knowledge_safely(
    query: str,
    *,
    fault_type: FaultType,
    k: int,
) -> list[KnowledgeRef]:
    return _run_knowledge_retrieval_tool(query, fault_type=fault_type, k=k).value


async def _retrieve_similar_incidents_safely(
    *,
    fault_type: FaultType,
    user_id: str | None,
    thread_id: str | None,
    limit: int,
) -> list[SimilarIncidentRef]:
    return (
        await _run_similar_incident_retrieval_tool(
            fault_type=fault_type,
            user_id=user_id,
            thread_id=thread_id,
            limit=limit,
        )
    ).value


def _trace_step(
    step: str,
    title: str,
    *,
    status: str = "success",
    detail: str | None = None,
    metadata: dict[str, str | int | float | bool | None] | None = None,
) -> AgentTraceStep:
    return AgentTraceStep(
        step=step,
        title=title,
        status=status,
        detail=detail,
        metadata=metadata or {},
    )


def _coerce_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _extract_token_usage(response: BaseMessage) -> dict[str, int]:
    usage_metadata = getattr(response, "usage_metadata", None) or {}
    response_metadata = getattr(response, "response_metadata", None) or {}
    token_usage = response_metadata.get("token_usage") or response_metadata.get("usage") or {}

    input_tokens = (
        _coerce_int(usage_metadata.get("input_tokens"))
        or _coerce_int(token_usage.get("input_tokens"))
        or _coerce_int(token_usage.get("prompt_tokens"))
    )
    output_tokens = (
        _coerce_int(usage_metadata.get("output_tokens"))
        or _coerce_int(token_usage.get("output_tokens"))
        or _coerce_int(token_usage.get("completion_tokens"))
    )
    total_tokens = (
        _coerce_int(usage_metadata.get("total_tokens"))
        or _coerce_int(token_usage.get("total_tokens"))
    )

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


def _estimate_token_cost_usd(token_usage: dict[str, int]) -> float | None:
    input_price = settings.LOGMIND_INPUT_TOKEN_PRICE_PER_1M_USD
    output_price = settings.LOGMIND_OUTPUT_TOKEN_PRICE_PER_1M_USD
    if input_price <= 0 and output_price <= 0:
        return None

    input_tokens = token_usage.get("input_tokens", 0)
    output_tokens = token_usage.get("output_tokens", 0)
    cost = (input_tokens / 1_000_000 * input_price) + (
        output_tokens / 1_000_000 * output_price
    )
    return round(cost, 8)


def _evaluate_diagnosis_quality(
    *,
    report_markdown: str,
    input_summary: str,
    fault_type: FaultType,
    severity: Severity,
    key_evidence: list[str],
    knowledge_refs: list[KnowledgeRef],
) -> DiagnosisQualityEvaluation:
    report_eval = evaluate_logmind_report_case(
        LogMindReportEvalCase(
            id="live_diagnosis",
            name="实时诊断质量评估",
            input_summary=input_summary,
            report_markdown=report_markdown,
            expected_fault_type=fault_type,
            expected_min_severity=severity,
            required_evidence=key_evidence,
            knowledge_refs=knowledge_refs,
        )
    )
    reference_accuracy = evaluate_knowledge_reference_accuracy(
        report_markdown=report_markdown,
        knowledge_refs=knowledge_refs,
    )

    return DiagnosisQualityEvaluation(
        quality_score=report_eval.quality_score,
        quality_breakdown=report_eval.quality_breakdown,
        reference_accuracy_passed=reference_accuracy.passed,
        cited_knowledge_titles=reference_accuracy.cited_titles,
        unsupported_knowledge_titles=reference_accuracy.unsupported_titles,
        fact_consistency_passed=report_eval.fact_consistency_passed,
        grounded_terms=report_eval.grounded_terms,
        ungrounded_terms=report_eval.ungrounded_terms,
        issues=report_eval.issues,
    )


def _build_diagnostic_system_prompt(
    *,
    fault_type: FaultType,
    knowledge_context: str,
    similar_incident_context: str,
) -> str:
    return dedent(
        f"""\
        你是 LogMind 智能日志分析与运维排障 Agent。
        请始终使用简体中文回答，面向日志分析、异常堆栈解析、故障诊断和修复建议场景。

        当前后端规则分类器给出的初步故障类型是：{fault_type.value}。
        该分类只作为辅助判断，不是最终结论；如果日志证据与分类不一致，请基于日志证据说明原因。

        以下是从 LogMind 运维知识库中检索到的参考片段：
        {knowledge_context}

        以下是相似历史诊断案例：
        {similar_incident_context}

        请优先结合用户日志、参考知识和相似历史案例进行分析。参考知识和历史案例只能作为辅助依据，不能替代当前日志证据；如果参考信息与当前日志不匹配，请明确说明。

        {DIAGNOSIS_OUTPUT_CONTRACT}

        注意：
        - 如果用户提供的信息较少，请说明判断基于有限信息。
        - 如果日志较长，请提取核心异常，不要逐行复述。
        - 不要编造命令结果。
        - 不要输出 API Key、密码、Token 等敏感信息。
        - 涉及生产环境时，提醒注意备份、权限和脱敏。
        - 参考知识部分只列出命中的知识标题和简短说明，不要大段复制知识库原文。
        """
    ).strip()


@entrypoint()
async def logmind(
    inputs: dict[str, list[BaseMessage]],
    *,
    previous: dict[str, list[BaseMessage]],
    config: RunnableConfig,
):
    runtime_started_at = perf_counter()
    messages = inputs["messages"]
    if previous:
        messages = previous["messages"] + messages
    latest_user_message = _message_text(inputs["messages"][-1]) if inputs["messages"] else ""
    sanitization_run = _run_input_sanitization_tool(
        messages=messages,
        latest_user_message=latest_user_message,
    )
    sanitized_messages, sanitized_latest_user_message = sanitization_run.value
    intent_run = _run_diagnostic_request_tool(sanitized_latest_user_message)
    diagnostic_request = intent_run.value
    agent_trace = [sanitization_run.trace_step, intent_run.trace_step]

    if not diagnostic_request:
        system_prompt = dedent(
            """\
            你是 LogMind 智能日志分析与运维排障 Agent。
            请使用简体中文自然回复。当前用户输入不像日志、异常堆栈或故障排查请求时，不要输出诊断报告模板。
            你可以简短说明自己可以帮助分析日志、异常堆栈、系统故障和运维排障问题。
            如果用户的问题与日志分析或运维排障无关，请礼貌说明你的主要能力边界，并引导用户提供日志、报错或故障现象。
            """
        ).strip()
        model = get_model(config["configurable"].get("model", settings.DEFAULT_MODEL))
        response = _sanitize_message(
            await model.ainvoke([SystemMessage(content=system_prompt)] + sanitized_messages)
        )
        return entrypoint.final(
            value={"messages": [response]},
            save={"messages": sanitized_messages + [response]},
        )

    configurable = config.get("configurable", {})
    thread_id = configurable.get("thread_id")
    user_id = configurable.get("user_id")

    classification_run = _run_fault_classification_tool(sanitized_latest_user_message)
    fault_type = classification_run.value
    agent_trace.append(classification_run.trace_step)

    knowledge_run = _run_knowledge_retrieval_tool(
        sanitized_latest_user_message,
        fault_type=fault_type,
        k=3,
    )
    knowledge_refs = knowledge_run.value
    agent_trace.append(knowledge_run.trace_step)
    knowledge_context = _format_knowledge_refs(knowledge_refs)
    similar_incident_run = await _run_similar_incident_retrieval_tool(
        fault_type=fault_type,
        user_id=user_id,
        thread_id=thread_id,
        limit=3,
    )
    similar_incidents = similar_incident_run.value
    agent_trace.append(similar_incident_run.trace_step)
    similar_incident_context = _format_similar_incidents(similar_incidents)
    system_prompt = _build_diagnostic_system_prompt(
        fault_type=fault_type,
        knowledge_context=knowledge_context,
        similar_incident_context=similar_incident_context,
    )

    selected_model = str(config["configurable"].get("model", settings.DEFAULT_MODEL))
    model = get_model(selected_model)

    async def _generate_report() -> BaseMessage:
        return _sanitize_message(
            await model.ainvoke([SystemMessage(content=system_prompt)] + sanitized_messages)
        )

    report_generation_run = await run_async_agent_tool(
        step="report_generation",
        title="诊断报告生成",
        tool_name="llm_generate_diagnosis_report",
        call=_generate_report,
        success_detail="调用模型生成 Markdown 诊断报告。",
        success_metadata=lambda generated_response: {
            "model": selected_model,
            "message_count": len(sanitized_messages),
            "tool_input_summary": f"messages={len(sanitized_messages)}, model={selected_model}",
            "tool_output_summary": _preview_text(str(generated_response.content)),
        },
    )
    response = report_generation_run.value
    model_latency_ms = report_generation_run.trace_step.metadata["tool_latency_ms"]
    report_generation_run.trace_step.metadata["model_latency_ms"] = model_latency_ms
    token_usage = _extract_token_usage(response)
    report_generation_run.trace_step.metadata.update(token_usage)
    estimated_cost_usd = _estimate_token_cost_usd(token_usage)
    if estimated_cost_usd is not None:
        report_generation_run.trace_step.metadata["estimated_cost_usd"] = estimated_cost_usd
    agent_trace.append(report_generation_run.trace_step)
    report_markdown = str(response.content)

    parsing_run = run_sync_agent_tool(
        step="structured_parsing",
        title="结构化字段解析",
        tool_name="parse_diagnosis_markdown",
        call=lambda: parse_diagnosis_markdown(
            report_markdown,
            fallback_summary=sanitized_latest_user_message[:500],
            fault_type=fault_type,
            severity=Severity.MEDIUM,
            knowledge_refs=knowledge_refs,
        ),
        success_detail="从 Markdown 报告中提取结构化诊断字段。",
        success_metadata=lambda parsed_report: {
            "fault_type": parsed_report.fault_type.value,
            "severity": parsed_report.severity.value,
            "key_evidence_count": len(parsed_report.key_evidence),
            "fix_suggestion_count": len(parsed_report.fix_suggestions),
            "tool_input_summary": "Markdown diagnosis report",
            "tool_output_summary": (
                f"fault_type={parsed_report.fault_type.value}, "
                f"severity={parsed_report.severity.value}"
            ),
        },
    )
    diagnosis_report = parsing_run.value
    agent_trace.append(parsing_run.trace_step)

    quality_run = run_sync_agent_tool(
        step="quality_evaluation",
        title="诊断质量评估",
        tool_name="evaluate_logmind_report_case",
        call=lambda: _evaluate_diagnosis_quality(
            report_markdown=report_markdown,
            input_summary=diagnosis_report.summary,
            fault_type=diagnosis_report.fault_type,
            severity=diagnosis_report.severity,
            key_evidence=diagnosis_report.key_evidence,
            knowledge_refs=diagnosis_report.knowledge_refs,
        ),
        success_detail=lambda evaluation: f"诊断报告质量分 {evaluation.quality_score}/100。",
        success_metadata=lambda evaluation: {
            "quality_score": evaluation.quality_score,
            "reference_accuracy_passed": evaluation.reference_accuracy_passed,
            "fact_consistency_passed": evaluation.fact_consistency_passed,
            "issue_count": len(evaluation.issues),
            "tool_input_summary": "structured diagnosis report",
            "tool_output_summary": f"quality_score={evaluation.quality_score}",
        },
    )
    quality_evaluation = quality_run.value
    agent_trace.append(
        quality_run.trace_step.model_copy(
            update={"status": "success" if not quality_evaluation.issues else "failed"}
        )
    )

    agent_trace.append(
        _trace_step(
            "diagnosis_record_save",
            "诊断记录保存",
            detail="保存诊断报告、结构化字段、知识引用和执行轨迹。",
            metadata={
                "tool_name": "save_diagnosis_record",
                "thread_id": thread_id,
                "user_id": user_id,
                "runtime_ms": round((perf_counter() - runtime_started_at) * 1000, 2),
                "tool_input_summary": "diagnosis report, refs, trace and quality evaluation",
                "tool_output_summary": "diagnosis record saved",
            },
        )
    )
    await save_diagnosis_record(
        input_summary=diagnosis_report.summary,
        report_markdown=report_markdown,
        fault_type=diagnosis_report.fault_type,
        severity=diagnosis_report.severity,
        thread_id=thread_id,
        user_id=user_id,
        model=selected_model,
        knowledge_refs=diagnosis_report.knowledge_refs,
        affected_component=diagnosis_report.affected_component,
        key_evidence=diagnosis_report.key_evidence,
        possible_causes=diagnosis_report.possible_causes,
        troubleshooting_steps=diagnosis_report.troubleshooting_steps,
        fix_suggestions=diagnosis_report.fix_suggestions,
        prevention_suggestions=diagnosis_report.prevention_suggestions,
        confidence=diagnosis_report.confidence,
        agent_trace=agent_trace,
        similar_incidents=similar_incidents,
        quality_evaluation=quality_evaluation,
    )
    return entrypoint.final(
        value={"messages": [response]},
        save={"messages": sanitized_messages + [response]},
    )
