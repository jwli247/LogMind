from collections.abc import Callable

from pydantic import BaseModel, Field

from core.logmind_eval import (
    LogMindEvalCase,
    LogMindRagEvalCase,
    LogMindReportEvalCase,
    evaluate_logmind_cases,
    evaluate_logmind_rag_cases,
    evaluate_logmind_report_cases,
)
from schema import FaultType, KnowledgeRef

RagRetriever = Callable[..., list[KnowledgeRef]]


class LogMindBaselineComparisonRow(BaseModel):
    strategy: str = Field(description="对比方案名称")
    description: str = Field(description="方案说明")
    classification_passed: int | None = Field(default=None, description="故障分类通过数")
    classification_total: int | None = Field(default=None, description="故障分类总数")
    classification_pass_rate: float | None = Field(default=None, description="故障分类通过率")
    rag_passed: int | None = Field(default=None, description="RAG 召回通过数")
    rag_total: int | None = Field(default=None, description="RAG 召回总数")
    rag_top3_recall: float | None = Field(default=None, description="RAG Top-3 平均召回率")
    report_eval_passed: int | None = Field(default=None, description="报告评估通过数")
    report_eval_total: int | None = Field(default=None, description="报告评估总数")
    report_eval_pass_rate: float | None = Field(default=None, description="报告评估通过率")
    trace_available: bool = Field(description="是否记录 Agent Trace")
    observability_available: bool = Field(description="是否提供运行观测")
    notes: list[str] = Field(default_factory=list, description="说明和边界")


class LogMindBaselineComparison(BaseModel):
    rows: list[LogMindBaselineComparisonRow]


def build_logmind_baseline_comparison(
    *,
    classification_cases: list[LogMindEvalCase],
    rag_cases: list[LogMindRagEvalCase],
    report_cases: list[LogMindReportEvalCase],
    rag_only_retriever: RagRetriever | None = None,
    agent_rag_retriever: RagRetriever | None = None,
) -> LogMindBaselineComparison:
    rag_only_summary = evaluate_logmind_rag_cases(
        rag_cases,
        retriever=rag_only_retriever or _retrieve_without_fault_filter,
    )
    agent_classification_summary = evaluate_logmind_cases(classification_cases)
    agent_rag_summary = evaluate_logmind_rag_cases(
        rag_cases,
        retriever=agent_rag_retriever,
    )
    agent_report_summary = evaluate_logmind_report_cases(report_cases)

    return LogMindBaselineComparison(
        rows=[
            LogMindBaselineComparisonRow(
                strategy="direct_llm",
                description="仅把日志交给模型，不接入规则分类、知识库和运行观测。",
                trace_available=False,
                observability_available=False,
                notes=[
                    "Offline eval does not call a live LLM, so generation quality is not scored.",
                    "Used as a capability baseline without regression classification or trace.",
                ],
            ),
            LogMindBaselineComparisonRow(
                strategy="rag_only",
                description="只做知识库检索，不使用故障类型过滤、历史案例和 Agent Trace。",
                rag_passed=rag_only_summary.passed,
                rag_total=rag_only_summary.total,
                rag_top3_recall=rag_only_summary.average_recall,
                trace_available=False,
                observability_available=False,
                notes=[
                    "Retrieval does not use fault_type filtering from the classifier.",
                    "Used to compare plain RAG retrieval against Agent-RAG retrieval.",
                ],
            ),
            LogMindBaselineComparisonRow(
                strategy="agent_rag",
                description="完整 LogMind 链路，包含规则分类、RAG、历史案例、结构化报告、Trace 和观测。",
                classification_passed=agent_classification_summary.passed,
                classification_total=agent_classification_summary.total,
                classification_pass_rate=agent_classification_summary.pass_rate,
                rag_passed=agent_rag_summary.passed,
                rag_total=agent_rag_summary.total,
                rag_top3_recall=agent_rag_summary.average_recall,
                report_eval_passed=agent_report_summary.passed,
                report_eval_total=agent_report_summary.total,
                report_eval_pass_rate=agent_report_summary.pass_rate,
                trace_available=True,
                observability_available=True,
                notes=[
                    "Fault type is used as a RAG filter.",
                    "Report quality, reference accuracy, fact consistency and observability are covered.",
                ],
            ),
        ]
    )


def _retrieve_without_fault_filter(
    query: str,
    *,
    fault_type: FaultType | None,
    k: int,
) -> list[KnowledgeRef]:
    from core.knowledge_base import retrieve_knowledge

    return retrieve_knowledge(query, fault_type=None, k=k)
