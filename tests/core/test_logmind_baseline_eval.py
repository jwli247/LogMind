from core.logmind_baseline_eval import build_logmind_baseline_comparison
from core.logmind_eval import (
    LogMindEvalCase,
    LogMindRagEvalCase,
    LogMindReportEvalCase,
)
from schema import FaultType, KnowledgeRef, Severity


def test_build_logmind_baseline_comparison_compares_rag_and_agent_rag() -> None:
    classification_cases = [
        LogMindEvalCase(
            id="port",
            name="端口冲突",
            input_text="Web server failed to start. Port 8080 was already in use.",
            expected_fault_type=FaultType.PORT_CONFLICT,
            expected_diagnostic_request=True,
            required_input_evidence=["Port 8080"],
        )
    ]
    rag_cases = [
        LogMindRagEvalCase(
            id="rag-port",
            name="端口知识召回",
            query="Port 8080 was already in use.",
            fault_type=FaultType.PORT_CONFLICT,
            expected_knowledge_titles=["端口冲突排查手册"],
        ),
        LogMindRagEvalCase(
            id="rag-timeout",
            name="超时知识召回",
            query="Read timed out.",
            fault_type=FaultType.TIMEOUT,
            expected_knowledge_titles=["超时问题排查手册"],
        ),
    ]
    report_cases = [
        LogMindReportEvalCase(
            id="report-port",
            name="端口报告",
            input_summary="Port 8080 was already in use.",
            expected_fault_type=FaultType.PORT_CONFLICT,
            expected_min_severity=Severity.MEDIUM,
            required_evidence=["Port 8080"],
            report_markdown="""## 1. 问题概述
- 故障类型：端口冲突
- 严重等级：中
- 影响组件：Web Server
- 简要说明：端口被占用。

## 2. 关键信息提取
- Port 8080 was already in use.

## 3. 可能原因分析
- 其他进程占用端口。

## 4. 建议排查步骤
- 检查端口占用。

## 5. 修复建议
- 释放端口。

## 6. 后续预防建议
- 规划端口。

## 7. 参考知识
- 未命中参考知识
""",
        )
    ]

    comparison = build_logmind_baseline_comparison(
        classification_cases=classification_cases,
        rag_cases=rag_cases,
        report_cases=report_cases,
        rag_only_retriever=_fake_rag_only_retriever,
        agent_rag_retriever=_fake_agent_rag_retriever,
    )

    rows = {row.strategy: row for row in comparison.rows}

    assert rows["direct_llm"].classification_pass_rate is None
    assert not rows["direct_llm"].trace_available
    assert rows["rag_only"].rag_top3_recall == 0.5
    assert not rows["rag_only"].observability_available
    assert rows["agent_rag"].classification_pass_rate == 1.0
    assert rows["agent_rag"].rag_top3_recall == 1.0
    assert rows["agent_rag"].report_eval_pass_rate == 1.0
    assert rows["agent_rag"].trace_available
    assert rows["agent_rag"].observability_available


def _fake_rag_only_retriever(
    query: str,
    *,
    fault_type: FaultType | None,
    k: int,
) -> list[KnowledgeRef]:
    if "Port" in query:
        return [KnowledgeRef(title="端口冲突排查手册")]

    return [KnowledgeRef(title="连接失败排查手册")]


def _fake_agent_rag_retriever(
    query: str,
    *,
    fault_type: FaultType | None,
    k: int,
) -> list[KnowledgeRef]:
    title_by_fault_type = {
        FaultType.PORT_CONFLICT: "端口冲突排查手册",
        FaultType.TIMEOUT: "超时问题排查手册",
    }
    return [KnowledgeRef(title=title_by_fault_type[fault_type])]
