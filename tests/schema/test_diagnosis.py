import pytest
from pydantic import ValidationError

from schema import (
    AgentTraceStep,
    DiagnosisQualityEvaluation,
    DiagnosisReport,
    FaultType,
    KnowledgeRef,
    Severity,
    SimilarIncidentRef,
)


def test_diagnosis_report_defaults_and_serialization() -> None:
    report = DiagnosisReport(summary="Spring Boot 端口 8080 被占用")

    assert report.fault_type == FaultType.UNKNOWN
    assert report.severity == Severity.MEDIUM
    assert report.key_evidence == []
    assert report.knowledge_refs == []
    assert report.agent_trace == []
    assert report.similar_incidents == []
    assert report.quality_evaluation is None

    dumped = report.model_dump(mode="json")
    assert dumped["summary"] == "Spring Boot 端口 8080 被占用"
    assert dumped["fault_type"] == "unknown"
    assert dumped["severity"] == "medium"


def test_diagnosis_report_accepts_known_fault_type_and_knowledge_refs() -> None:
    report = DiagnosisReport(
        summary="Web server failed to start because port 8080 was already in use.",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.LOW,
        affected_component="Spring Boot Web Server",
        key_evidence=["Port 8080 was already in use"],
        possible_causes=["旧服务实例未退出", "其他进程占用了 8080 端口"],
        troubleshooting_steps=["netstat -ano | findstr :8080"],
        fix_suggestions=["停止占用端口的进程，或修改 server.port"],
        prevention_suggestions=["为本地服务统一规划端口"],
        confidence=0.9,
        knowledge_refs=[
            KnowledgeRef(
                title="Spring Boot 端口冲突排查手册",
                source="internal-runbook",
                snippet="Web server failed to start usually indicates port binding failure.",
            )
        ],
        agent_trace=[
            AgentTraceStep(
                step="knowledge_retrieval",
                title="知识库检索",
                metadata={"hit_count": 1},
            )
        ],
        similar_incidents=[
            SimilarIncidentRef(
                record_id="record-1",
                fault_type=FaultType.PORT_CONFLICT,
                severity=Severity.LOW,
                summary="历史端口冲突案例",
                created_at="2026-07-31T10:00:00+00:00",
                thread_id="thread-1",
            )
        ],
        quality_evaluation=DiagnosisQualityEvaluation(
            quality_score=95,
            quality_breakdown={"sections": 20, "evidence": 20},
            reference_accuracy_passed=True,
            cited_knowledge_titles=["Spring Boot 端口冲突排查手册"],
        ),
    )

    assert report.fault_type == FaultType.PORT_CONFLICT
    assert report.severity == Severity.LOW
    assert report.knowledge_refs[0].title == "Spring Boot 端口冲突排查手册"
    assert report.agent_trace[0].step == "knowledge_retrieval"
    assert report.similar_incidents[0].record_id == "record-1"
    assert report.quality_evaluation is not None
    assert report.quality_evaluation.quality_score == 95


def test_diagnosis_report_rejects_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        DiagnosisReport(summary="置信度越界", confidence=1.5)


def test_diagnosis_report_rejects_unknown_enum_value() -> None:
    with pytest.raises(ValidationError):
        DiagnosisReport(summary="未知故障类型", fault_type="not_a_real_fault_type")
