from core.diagnosis_export import build_diagnosis_markdown_export, diagnosis_export_filename
from schema import (
    AgentTraceStep,
    DiagnosisRecord,
    FaultType,
    KnowledgeRef,
    Severity,
    SimilarIncidentRef,
)


def test_build_diagnosis_markdown_export_includes_record_details() -> None:
    record = DiagnosisRecord(
        id="record-1",
        thread_id="thread-1",
        user_id="user-1",
        summary="Port 8080 is already in use.",
        report_markdown="## 1. 问题概述\n端口冲突导致启动失败。",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.HIGH,
        affected_component="Spring Boot Web Server",
        key_evidence=["Port 8080 was already in use."],
        possible_causes=["Another process is listening on 8080."],
        troubleshooting_steps=["Run netstat to find the process."],
        fix_suggestions=["Stop the process or change server.port."],
        prevention_suggestions=["Reserve ports for local services."],
        confidence=0.9,
        knowledge_refs=[
            KnowledgeRef(
                title="Port conflict guide",
                source="docs/knowledge/port_conflict.md",
                snippet="Find and stop the process listening on the port.",
            )
        ],
        agent_trace=[
            AgentTraceStep(
                step="knowledge_retrieval",
                title="知识库检索",
                detail="检索到 1 条参考知识。",
                metadata={"hit_count": 1},
            )
        ],
        similar_incidents=[
            SimilarIncidentRef(
                record_id="history-record",
                fault_type=FaultType.PORT_CONFLICT,
                severity=Severity.HIGH,
                summary="历史端口冲突案例",
                created_at="2026-07-31T10:00:00+00:00",
                thread_id="history-thread",
            )
        ],
        model="openai-compatible",
        created_at="2026-07-28T14:00:00+00:00",
    )

    markdown = build_diagnosis_markdown_export(record)

    assert "# LogMind 诊断报告" in markdown
    assert "- 记录 ID：record-1" in markdown
    assert "- 故障类型：port_conflict" in markdown
    assert "- 严重等级：high" in markdown
    assert "- 影响组件：Spring Boot Web Server" in markdown
    assert "- Port 8080 was already in use." in markdown
    assert "Port conflict guide" in markdown
    assert "## 相似历史案例" in markdown
    assert "历史端口冲突案例" in markdown
    assert "## Agent 执行轨迹" in markdown
    assert "知识库检索" in markdown
    assert "hit_count=1" in markdown
    assert "## 完整报告" in markdown
    assert "端口冲突导致启动失败。" in markdown


def test_diagnosis_export_filename_sanitizes_record_id() -> None:
    record = DiagnosisRecord(
        id="record/with space",
        summary="summary",
        report_markdown="report",
        fault_type=FaultType.UNKNOWN,
        severity=Severity.MEDIUM,
        created_at="2026-07-28T14:00:00+00:00",
    )

    assert diagnosis_export_filename(record) == "logmind-diagnosis-record-with-space.md"
