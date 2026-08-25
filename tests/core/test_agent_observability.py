from core.agent_observability import build_agent_observability_summary
from schema import (
    AgentTraceStep,
    DiagnosisQualityEvaluation,
    DiagnosisRecord,
    FaultType,
    KnowledgeRef,
    Severity,
    SimilarIncidentRef,
)


def test_build_agent_observability_summary_returns_zero_state() -> None:
    summary = build_agent_observability_summary([])

    assert summary.total_records == 0
    assert summary.trace_coverage_rate == 0.0
    assert summary.knowledge_hit_rate == 0.0
    assert summary.step_stats == []


def test_build_agent_observability_summary_aggregates_trace_and_hits() -> None:
    records = [
        _record(
            "record-1",
            knowledge_refs=[
                KnowledgeRef(
                    title="端口冲突排查手册",
                    source="docs/knowledge/port_conflict.md",
                    snippet="确认端口占用。",
                )
            ],
            similar_incidents=[
                SimilarIncidentRef(
                    record_id="history-1",
                    fault_type=FaultType.PORT_CONFLICT,
                    severity=Severity.MEDIUM,
                    summary="历史端口冲突",
                    created_at="2026-07-31T00:00:00+00:00",
                )
            ],
            agent_trace=[
                AgentTraceStep(step="intent_detection", title="诊断请求识别"),
                AgentTraceStep(
                    step="report_generation",
                    title="诊断报告生成",
                    metadata={
                        "model_latency_ms": 1200.0,
                        "input_tokens": 1000,
                        "output_tokens": 500,
                        "total_tokens": 1500,
                        "estimated_cost_usd": 0.001,
                    },
                ),
                AgentTraceStep(step="knowledge_retrieval", title="知识库检索"),
                AgentTraceStep(
                    step="diagnosis_record_save",
                    title="诊断记录保存",
                    metadata={"runtime_ms": 1800.0},
                ),
            ],
            quality_evaluation=DiagnosisQualityEvaluation(
                quality_score=92,
                quality_breakdown={"sections": 20},
                reference_accuracy_passed=True,
            ),
        ),
        _record(
            "record-2",
            quality_evaluation=DiagnosisQualityEvaluation(
                quality_score=62,
                quality_breakdown={"sections": 10},
                reference_accuracy_passed=False,
                unsupported_knowledge_titles=["不存在的手册"],
                issues=["unsupported knowledge references: 不存在的手册"],
            ),
            agent_trace=[
                AgentTraceStep(step="intent_detection", title="诊断请求识别"),
                AgentTraceStep(
                    step="knowledge_retrieval",
                    title="知识库检索",
                    status="failed",
                    detail="知识库连接失败，已降级为纯日志诊断。",
                ),
            ],
        ),
        _record("record-3"),
    ]

    summary = build_agent_observability_summary(records)

    assert summary.total_records == 3
    assert summary.records_with_trace == 2
    assert summary.trace_coverage_rate == 0.6667
    assert summary.total_trace_steps == 6
    assert summary.average_trace_steps_per_record == 2.0
    assert summary.failed_trace_records == 1
    assert summary.failed_trace_steps == 1
    assert summary.knowledge_hit_records == 1
    assert summary.knowledge_hit_rate == 0.3333
    assert summary.similar_incident_hit_records == 1
    assert summary.similar_incident_hit_rate == 0.3333
    assert summary.quality_evaluated_records == 2
    assert summary.average_quality_score == 77.0
    assert summary.average_runtime_ms == 1800.0
    assert summary.p95_runtime_ms == 1800.0
    assert summary.average_model_latency_ms == 1200.0
    assert summary.p95_model_latency_ms == 1200.0
    assert summary.token_usage_records == 1
    assert summary.total_input_tokens == 1000
    assert summary.total_output_tokens == 500
    assert summary.total_tokens == 1500
    assert summary.average_total_tokens == 1500.0
    assert summary.total_estimated_cost_usd == 0.001
    assert summary.average_estimated_cost_usd == 0.001
    assert summary.low_quality_records == 1
    assert summary.reference_accuracy_failed_records == 1
    assert summary.failure_reasons == ["知识库连接失败，已降级为纯日志诊断。 (1)"]

    step_stats = {step.step: step for step in summary.step_stats}
    assert step_stats["intent_detection"].success == 2
    assert step_stats["knowledge_retrieval"].success == 1
    assert step_stats["knowledge_retrieval"].failed == 1


def _record(
    record_id: str,
    *,
    knowledge_refs: list[KnowledgeRef] | None = None,
    similar_incidents: list[SimilarIncidentRef] | None = None,
    agent_trace: list[AgentTraceStep] | None = None,
    quality_evaluation: DiagnosisQualityEvaluation | None = None,
) -> DiagnosisRecord:
    return DiagnosisRecord(
        id=record_id,
        thread_id="thread-1",
        user_id="user-1",
        summary="Web server failed to start. Port 8080 was already in use.",
        report_markdown="## report",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.MEDIUM,
        model="openai-compatible",
        created_at="2026-07-31T00:00:00+00:00",
        knowledge_refs=knowledge_refs or [],
        similar_incidents=similar_incidents or [],
        agent_trace=agent_trace or [],
        quality_evaluation=quality_evaluation,
    )
