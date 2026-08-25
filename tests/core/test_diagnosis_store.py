import json
import sqlite3

import pytest

from core.diagnosis_store import (
    get_diagnosis_record,
    get_diagnosis_stats,
    init_diagnosis_store,
    list_diagnosis_records,
    list_similar_diagnosis_records,
    save_diagnosis_record,
)
from schema import (
    AgentTraceStep,
    DiagnosisQualityEvaluation,
    FaultType,
    KnowledgeRef,
    Severity,
    SimilarIncidentRef,
)


@pytest.mark.asyncio
async def test_init_diagnosis_store_creates_table(tmp_path) -> None:
    db_path = tmp_path / "diagnosis.db"

    await init_diagnosis_store(str(db_path))

    with sqlite3.connect(db_path) as conn:
        table = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'diagnosis_records'
            """
        ).fetchone()

    assert table == ("diagnosis_records",)


@pytest.mark.asyncio
async def test_save_diagnosis_record_inserts_record(tmp_path) -> None:
    db_path = tmp_path / "diagnosis.db"

    record_id = await save_diagnosis_record(
        input_summary="Spring Boot 端口 8080 被占用",
        report_markdown="## 1. 问题概述\n端口冲突导致启动失败。",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.LOW,
        thread_id="thread-1",
        user_id="user-1",
        model="openai-compatible",
        db_path=str(db_path),
    )

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT
                id, thread_id, user_id, fault_type, severity,
                input_summary, report_markdown, model, created_at
            FROM diagnosis_records
            WHERE id = ?
            """,
            (record_id,),
        ).fetchone()

    assert row is not None
    assert row[0] == record_id
    assert row[1] == "thread-1"
    assert row[2] == "user-1"
    assert row[3] == "port_conflict"
    assert row[4] == "low"
    assert row[5] == "Spring Boot 端口 8080 被占用"
    assert row[6] == "## 1. 问题概述\n端口冲突导致启动失败。"
    assert row[7] == "openai-compatible"
    assert row[8]


@pytest.mark.asyncio
async def test_list_diagnosis_records_returns_recent_records_first(tmp_path) -> None:
    db_path = tmp_path / "diagnosis.db"

    first_id = await save_diagnosis_record(
        input_summary="第一条诊断",
        report_markdown="第一条报告",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.LOW,
        db_path=str(db_path),
    )
    second_id = await save_diagnosis_record(
        input_summary="第二条诊断",
        report_markdown="第二条报告",
        fault_type=FaultType.REDIS_CONNECTION,
        severity=Severity.HIGH,
        db_path=str(db_path),
    )

    records = await list_diagnosis_records(db_path=str(db_path))

    assert [record.id for record in records] == [second_id, first_id]
    assert records[0].summary == "第二条诊断"
    assert records[0].report_markdown == "第二条报告"
    assert records[0].fault_type == FaultType.REDIS_CONNECTION
    assert records[0].severity == Severity.HIGH


@pytest.mark.asyncio
async def test_list_diagnosis_records_filters_by_fault_type(tmp_path) -> None:
    db_path = tmp_path / "diagnosis.db"

    await save_diagnosis_record(
        input_summary="端口冲突诊断",
        report_markdown="端口冲突报告",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.LOW,
        db_path=str(db_path),
    )
    redis_id = await save_diagnosis_record(
        input_summary="Redis 连接诊断",
        report_markdown="Redis 连接报告",
        fault_type=FaultType.REDIS_CONNECTION,
        severity=Severity.HIGH,
        db_path=str(db_path),
    )

    records = await list_diagnosis_records(
        fault_type=FaultType.REDIS_CONNECTION,
        db_path=str(db_path),
    )

    assert len(records) == 1
    assert records[0].id == redis_id
    assert records[0].fault_type == FaultType.REDIS_CONNECTION
    assert records[0].summary == "Redis 连接诊断"


@pytest.mark.asyncio
async def test_save_and_list_diagnosis_records_preserves_knowledge_refs(tmp_path) -> None:
    db_path = tmp_path / "diagnosis.db"
    knowledge_ref = KnowledgeRef(
        title="Port conflict guide",
        source="docs/knowledge/port_conflict.md",
        snippet="Check which process is listening on the port.",
    )

    record_id = await save_diagnosis_record(
        input_summary="port 8080 already in use",
        report_markdown="## report",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.LOW,
        knowledge_refs=[knowledge_ref],
        db_path=str(db_path),
    )

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT knowledge_refs FROM diagnosis_records WHERE id = ?",
            (record_id,),
        ).fetchone()

    assert row is not None
    assert json.loads(row[0]) == [knowledge_ref.model_dump(mode="json")]

    records = await list_diagnosis_records(db_path=str(db_path))

    assert records[0].id == record_id
    assert records[0].knowledge_refs == [knowledge_ref]


@pytest.mark.asyncio
async def test_save_and_list_diagnosis_records_preserves_structured_fields(tmp_path) -> None:
    db_path = tmp_path / "diagnosis.db"

    record_id = await save_diagnosis_record(
        input_summary="Web 服务启动失败，8080 端口已被占用。",
        report_markdown="## report",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.HIGH,
        affected_component="Spring Boot Web Server",
        key_evidence=["Web server failed to start.", "Port 8080 was already in use."],
        possible_causes=["旧服务实例没有退出。"],
        troubleshooting_steps=["执行 netstat -ano | findstr :8080。"],
        fix_suggestions=["停止占用端口的进程。"],
        prevention_suggestions=["为本地服务统一规划端口。"],
        confidence=0.85,
        db_path=str(db_path),
    )

    records = await list_diagnosis_records(db_path=str(db_path))

    assert records[0].id == record_id
    assert records[0].summary == "Web 服务启动失败，8080 端口已被占用。"
    assert records[0].severity == Severity.HIGH
    assert records[0].affected_component == "Spring Boot Web Server"
    assert records[0].key_evidence == [
        "Web server failed to start.",
        "Port 8080 was already in use.",
    ]
    assert records[0].possible_causes == ["旧服务实例没有退出。"]
    assert records[0].troubleshooting_steps == ["执行 netstat -ano | findstr :8080。"]
    assert records[0].fix_suggestions == ["停止占用端口的进程。"]
    assert records[0].prevention_suggestions == ["为本地服务统一规划端口。"]
    assert records[0].confidence == 0.85


@pytest.mark.asyncio
async def test_save_and_list_diagnosis_records_preserves_agent_trace(tmp_path) -> None:
    db_path = tmp_path / "diagnosis.db"
    trace_step = AgentTraceStep(
        step="knowledge_retrieval",
        title="知识库检索",
        detail="检索到 1 条参考知识。",
        metadata={"hit_count": 1},
    )

    record_id = await save_diagnosis_record(
        input_summary="port 8080 already in use",
        report_markdown="## report",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.HIGH,
        agent_trace=[trace_step],
        db_path=str(db_path),
    )

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT agent_trace FROM diagnosis_records WHERE id = ?",
            (record_id,),
        ).fetchone()

    assert row is not None
    assert json.loads(row[0]) == [trace_step.model_dump(mode="json")]

    records = await list_diagnosis_records(db_path=str(db_path))

    assert records[0].agent_trace == [trace_step]


@pytest.mark.asyncio
async def test_save_and_list_diagnosis_records_preserves_similar_incidents(tmp_path) -> None:
    db_path = tmp_path / "diagnosis.db"
    incident = SimilarIncidentRef(
        record_id="history-record",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.HIGH,
        summary="历史端口冲突案例",
        created_at="2026-07-31T10:00:00+00:00",
        thread_id="history-thread",
    )

    record_id = await save_diagnosis_record(
        input_summary="port 8080 already in use",
        report_markdown="## report",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.HIGH,
        similar_incidents=[incident],
        db_path=str(db_path),
    )

    records = await list_diagnosis_records(db_path=str(db_path))

    assert records[0].id == record_id
    assert records[0].similar_incidents == [incident]


@pytest.mark.asyncio
async def test_save_and_list_diagnosis_records_preserves_quality_evaluation(tmp_path) -> None:
    db_path = tmp_path / "diagnosis.db"
    quality_evaluation = DiagnosisQualityEvaluation(
        quality_score=88,
        quality_breakdown={
            "sections": 20,
            "evidence": 18,
            "references": 5,
        },
        reference_accuracy_passed=False,
        cited_knowledge_titles=["端口冲突排查手册", "不存在的手册"],
        unsupported_knowledge_titles=["不存在的手册"],
        issues=["unsupported knowledge references: 不存在的手册"],
    )

    record_id = await save_diagnosis_record(
        input_summary="port 8080 already in use",
        report_markdown="## report",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.HIGH,
        quality_evaluation=quality_evaluation,
        db_path=str(db_path),
    )

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT quality_evaluation FROM diagnosis_records WHERE id = ?",
            (record_id,),
        ).fetchone()

    assert row is not None
    assert json.loads(row[0]) == quality_evaluation.model_dump(mode="json")

    records = await list_diagnosis_records(db_path=str(db_path))

    assert records[0].quality_evaluation == quality_evaluation


@pytest.mark.asyncio
async def test_list_similar_diagnosis_records_filters_history(tmp_path) -> None:
    db_path = tmp_path / "diagnosis.db"

    matching_id = await save_diagnosis_record(
        input_summary="历史端口冲突案例",
        report_markdown="matching report",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.HIGH,
        thread_id="history-thread",
        user_id="user-a",
        db_path=str(db_path),
    )
    await save_diagnosis_record(
        input_summary="当前会话端口冲突案例",
        report_markdown="same thread report",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.LOW,
        thread_id="current-thread",
        user_id="user-a",
        db_path=str(db_path),
    )
    await save_diagnosis_record(
        input_summary="其他用户端口冲突案例",
        report_markdown="other user report",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.LOW,
        thread_id="other-thread",
        user_id="user-b",
        db_path=str(db_path),
    )
    await save_diagnosis_record(
        input_summary="配置错误案例",
        report_markdown="config report",
        fault_type=FaultType.CONFIGURATION_ERROR,
        severity=Severity.LOW,
        thread_id="config-thread",
        user_id="user-a",
        db_path=str(db_path),
    )

    incidents = await list_similar_diagnosis_records(
        fault_type=FaultType.PORT_CONFLICT,
        user_id="user-a",
        exclude_thread_id="current-thread",
        db_path=str(db_path),
    )

    assert len(incidents) == 1
    assert incidents[0].record_id == matching_id
    assert incidents[0].summary == "历史端口冲突案例"


@pytest.mark.asyncio
async def test_list_diagnosis_records_filters_by_thread_and_user(tmp_path) -> None:
    db_path = tmp_path / "diagnosis.db"

    matching_id = await save_diagnosis_record(
        input_summary="matching diagnosis",
        report_markdown="matching report",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.LOW,
        thread_id="thread-a",
        user_id="user-a",
        db_path=str(db_path),
    )
    await save_diagnosis_record(
        input_summary="same thread different user",
        report_markdown="other report",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.LOW,
        thread_id="thread-a",
        user_id="user-b",
        db_path=str(db_path),
    )
    await save_diagnosis_record(
        input_summary="same user different thread",
        report_markdown="other report",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.LOW,
        thread_id="thread-b",
        user_id="user-a",
        db_path=str(db_path),
    )

    records = await list_diagnosis_records(
        thread_id="thread-a",
        user_id="user-a",
        db_path=str(db_path),
    )

    assert [record.id for record in records] == [matching_id]


@pytest.mark.asyncio
async def test_get_diagnosis_record_returns_record_by_id(tmp_path) -> None:
    db_path = tmp_path / "diagnosis.db"

    record_id = await save_diagnosis_record(
        input_summary="lookup diagnosis",
        report_markdown="lookup report",
        fault_type=FaultType.CONFIGURATION_ERROR,
        severity=Severity.MEDIUM,
        thread_id="thread-lookup",
        user_id="user-lookup",
        db_path=str(db_path),
    )

    record = await get_diagnosis_record(record_id, db_path=str(db_path))
    missing_record = await get_diagnosis_record("missing-record", db_path=str(db_path))

    assert record is not None
    assert record.id == record_id
    assert record.thread_id == "thread-lookup"
    assert record.user_id == "user-lookup"
    assert missing_record is None


@pytest.mark.asyncio
async def test_get_diagnosis_stats_returns_aggregates(tmp_path) -> None:
    db_path = tmp_path / "diagnosis.db"

    await save_diagnosis_record(
        input_summary="port diagnosis",
        report_markdown="port report",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.MEDIUM,
        thread_id="thread-a",
        user_id="user-a",
        db_path=str(db_path),
    )
    await save_diagnosis_record(
        input_summary="second port diagnosis",
        report_markdown="second port report",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.HIGH,
        thread_id="thread-a",
        user_id="user-a",
        db_path=str(db_path),
    )
    await save_diagnosis_record(
        input_summary="redis diagnosis",
        report_markdown="redis report",
        fault_type=FaultType.REDIS_CONNECTION,
        severity=Severity.HIGH,
        thread_id="thread-b",
        user_id="user-b",
        db_path=str(db_path),
    )

    stats = await get_diagnosis_stats(days=7, db_path=str(db_path))

    assert stats.total == 3
    assert stats.by_fault_type == {
        "port_conflict": 2,
        "redis_connection": 1,
    }
    assert stats.by_severity == {
        "high": 2,
        "medium": 1,
    }
    assert sum(day.count for day in stats.daily_counts) == 3


@pytest.mark.asyncio
async def test_get_diagnosis_stats_filters_by_thread_and_user(tmp_path) -> None:
    db_path = tmp_path / "diagnosis.db"

    await save_diagnosis_record(
        input_summary="matching diagnosis",
        report_markdown="matching report",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.MEDIUM,
        thread_id="thread-a",
        user_id="user-a",
        db_path=str(db_path),
    )
    await save_diagnosis_record(
        input_summary="same thread different user",
        report_markdown="other report",
        fault_type=FaultType.REDIS_CONNECTION,
        severity=Severity.HIGH,
        thread_id="thread-a",
        user_id="user-b",
        db_path=str(db_path),
    )
    await save_diagnosis_record(
        input_summary="same user different thread",
        report_markdown="other report",
        fault_type=FaultType.CONFIGURATION_ERROR,
        severity=Severity.LOW,
        thread_id="thread-b",
        user_id="user-a",
        db_path=str(db_path),
    )

    stats = await get_diagnosis_stats(
        days=7,
        thread_id="thread-a",
        user_id="user-a",
        db_path=str(db_path),
    )

    assert stats.total == 1
    assert stats.by_fault_type == {"port_conflict": 1}
    assert stats.by_severity == {"medium": 1}
