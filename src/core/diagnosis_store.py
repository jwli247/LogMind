import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import aiosqlite

from core import settings
from schema import (
    AgentTraceStep,
    DiagnosisDailyCount,
    DiagnosisQualityEvaluation,
    DiagnosisRecord,
    DiagnosisStats,
    FaultType,
    KnowledgeRef,
    Severity,
    SimilarIncidentRef,
)

CREATE_DIAGNOSIS_RECORDS_TABLE = """
CREATE TABLE IF NOT EXISTS diagnosis_records (
    id TEXT PRIMARY KEY,
    thread_id TEXT,
    user_id TEXT,
    fault_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    input_summary TEXT NOT NULL,
    report_markdown TEXT NOT NULL,
    model TEXT,
    created_at TEXT NOT NULL,
    knowledge_refs TEXT NOT NULL DEFAULT '[]',
    affected_component TEXT,
    key_evidence TEXT NOT NULL DEFAULT '[]',
    possible_causes TEXT NOT NULL DEFAULT '[]',
    troubleshooting_steps TEXT NOT NULL DEFAULT '[]',
    fix_suggestions TEXT NOT NULL DEFAULT '[]',
    prevention_suggestions TEXT NOT NULL DEFAULT '[]',
    confidence REAL,
    agent_trace TEXT NOT NULL DEFAULT '[]',
    similar_incidents TEXT NOT NULL DEFAULT '[]',
    quality_evaluation TEXT
)
"""


DIAGNOSIS_RECORD_COLUMNS = """
    id, thread_id, user_id, fault_type, severity,
    input_summary, report_markdown, model, created_at,
    knowledge_refs, affected_component, key_evidence,
    possible_causes, troubleshooting_steps, fix_suggestions,
    prevention_suggestions, confidence, agent_trace, similar_incidents,
    quality_evaluation
"""


DIAGNOSIS_SCHEMA_COLUMNS = {
    "knowledge_refs": "TEXT NOT NULL DEFAULT '[]'",
    "affected_component": "TEXT",
    "key_evidence": "TEXT NOT NULL DEFAULT '[]'",
    "possible_causes": "TEXT NOT NULL DEFAULT '[]'",
    "troubleshooting_steps": "TEXT NOT NULL DEFAULT '[]'",
    "fix_suggestions": "TEXT NOT NULL DEFAULT '[]'",
    "prevention_suggestions": "TEXT NOT NULL DEFAULT '[]'",
    "confidence": "REAL",
    "agent_trace": "TEXT NOT NULL DEFAULT '[]'",
    "similar_incidents": "TEXT NOT NULL DEFAULT '[]'",
    "quality_evaluation": "TEXT",
}


async def _ensure_diagnosis_schema(db: aiosqlite.Connection) -> None:
    columns = await db.execute_fetchall("PRAGMA table_info(diagnosis_records)")
    column_names = {column[1] for column in columns}

    for column_name, column_definition in DIAGNOSIS_SCHEMA_COLUMNS.items():
        if column_name not in column_names:
            await db.execute(
                f"ALTER TABLE diagnosis_records ADD COLUMN {column_name} {column_definition}"
            )


async def init_diagnosis_store(db_path: str | None = None) -> None:
    path = db_path or settings.SQLITE_DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(path) as db:
        await db.execute(CREATE_DIAGNOSIS_RECORDS_TABLE)
        await _ensure_diagnosis_schema(db)
        await db.commit()


def _row_to_diagnosis_record(row) -> DiagnosisRecord:
    return DiagnosisRecord(
        id=row[0],
        thread_id=row[1],
        user_id=row[2],
        fault_type=FaultType(row[3]),
        severity=Severity(row[4]),
        summary=row[5],
        report_markdown=row[6],
        model=row[7],
        created_at=row[8],
        knowledge_refs=[
            KnowledgeRef.model_validate(ref) for ref in json.loads(row[9] or "[]")
        ],
        affected_component=row[10],
        key_evidence=json.loads(row[11] or "[]"),
        possible_causes=json.loads(row[12] or "[]"),
        troubleshooting_steps=json.loads(row[13] or "[]"),
        fix_suggestions=json.loads(row[14] or "[]"),
        prevention_suggestions=json.loads(row[15] or "[]"),
        confidence=row[16],
        agent_trace=[
            AgentTraceStep.model_validate(step) for step in json.loads(row[17] or "[]")
        ],
        similar_incidents=[
            SimilarIncidentRef.model_validate(incident)
            for incident in json.loads(row[18] or "[]")
        ],
        quality_evaluation=(
            DiagnosisQualityEvaluation.model_validate(json.loads(row[19]))
            if row[19]
            else None
        ),
    )


async def save_diagnosis_record(
    *,
    input_summary: str,
    report_markdown: str,
    fault_type: FaultType = FaultType.UNKNOWN,
    severity: Severity = Severity.MEDIUM,
    thread_id: str | None = None,
    user_id: str | None = None,
    model: str | None = None,
    knowledge_refs: list[KnowledgeRef] | None = None,
    affected_component: str | None = None,
    key_evidence: list[str] | None = None,
    possible_causes: list[str] | None = None,
    troubleshooting_steps: list[str] | None = None,
    fix_suggestions: list[str] | None = None,
    prevention_suggestions: list[str] | None = None,
    confidence: float | None = None,
    agent_trace: list[AgentTraceStep] | None = None,
    similar_incidents: list[SimilarIncidentRef] | None = None,
    quality_evaluation: DiagnosisQualityEvaluation | None = None,
    db_path: str | None = None,
) -> str:
    path = db_path or settings.SQLITE_DB_PATH
    record_id = str(uuid4())
    created_at = datetime.now(UTC).isoformat()

    await init_diagnosis_store(path)

    knowledge_refs_json = json.dumps(
        [ref.model_dump(mode="json") for ref in (knowledge_refs or [])],
        ensure_ascii=False,
    )
    key_evidence_json = _dump_string_list(key_evidence)
    possible_causes_json = _dump_string_list(possible_causes)
    troubleshooting_steps_json = _dump_string_list(troubleshooting_steps)
    fix_suggestions_json = _dump_string_list(fix_suggestions)
    prevention_suggestions_json = _dump_string_list(prevention_suggestions)
    agent_trace_json = json.dumps(
        [step.model_dump(mode="json") for step in (agent_trace or [])],
        ensure_ascii=False,
    )
    similar_incidents_json = json.dumps(
        [incident.model_dump(mode="json") for incident in (similar_incidents or [])],
        ensure_ascii=False,
    )
    quality_evaluation_json = (
        json.dumps(quality_evaluation.model_dump(mode="json"), ensure_ascii=False)
        if quality_evaluation
        else None
    )

    async with aiosqlite.connect(path) as db:
        await db.execute(
            """
            INSERT INTO diagnosis_records (
                id, thread_id, user_id, fault_type, severity,
                input_summary, report_markdown, model, created_at,
                knowledge_refs, affected_component, key_evidence,
                possible_causes, troubleshooting_steps, fix_suggestions,
                prevention_suggestions, confidence, agent_trace, similar_incidents,
                quality_evaluation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                thread_id,
                user_id,
                fault_type.value,
                severity.value,
                input_summary,
                report_markdown,
                model,
                created_at,
                knowledge_refs_json,
                affected_component,
                key_evidence_json,
                possible_causes_json,
                troubleshooting_steps_json,
                fix_suggestions_json,
                prevention_suggestions_json,
                confidence,
                agent_trace_json,
                similar_incidents_json,
                quality_evaluation_json,
            ),
        )
        await db.commit()

    return record_id


def _dump_string_list(values: list[str] | None) -> str:
    return json.dumps(values or [], ensure_ascii=False)

async def list_diagnosis_records(
    *,
    limit: int = 20,
    fault_type: FaultType | None = None,
    thread_id: str | None = None,
    user_id: str | None = None,
    db_path: str | None = None,
) -> list[DiagnosisRecord]:
    path = db_path or settings.SQLITE_DB_PATH
    await init_diagnosis_store(path)

    query = f"SELECT {DIAGNOSIS_RECORD_COLUMNS} FROM diagnosis_records"
    params: list[str | int] = []
    filters: list[str] = []

    if fault_type is not None:
        filters.append("fault_type = ?")
        params.append(fault_type.value)

    if thread_id is not None:
        filters.append("thread_id = ?")
        params.append(thread_id)

    if user_id is not None:
        filters.append("user_id = ?")
        params.append(user_id)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    async with aiosqlite.connect(path) as db:
        rows = await db.execute_fetchall(query, params)

    return [_row_to_diagnosis_record(row) for row in rows]


async def list_similar_diagnosis_records(
    *,
    fault_type: FaultType,
    limit: int = 3,
    user_id: str | None = None,
    exclude_thread_id: str | None = None,
    db_path: str | None = None,
) -> list[SimilarIncidentRef]:
    path = db_path or settings.SQLITE_DB_PATH
    await init_diagnosis_store(path)

    query = """
        SELECT id, fault_type, severity, input_summary, created_at, thread_id
        FROM diagnosis_records
        WHERE fault_type = ?
    """
    params: list[str | int] = [fault_type.value]

    if user_id is not None:
        query += " AND user_id = ?"
        params.append(user_id)

    if exclude_thread_id is not None:
        query += " AND (thread_id IS NULL OR thread_id != ?)"
        params.append(exclude_thread_id)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    async with aiosqlite.connect(path) as db:
        rows = await db.execute_fetchall(query, params)

    return [
        SimilarIncidentRef(
            record_id=row[0],
            fault_type=FaultType(row[1]),
            severity=Severity(row[2]),
            summary=row[3],
            created_at=row[4],
            thread_id=row[5],
        )
        for row in rows
    ]


async def get_diagnosis_record(
    record_id: str,
    *,
    db_path: str | None = None,
) -> DiagnosisRecord | None:
    path = db_path or settings.SQLITE_DB_PATH
    await init_diagnosis_store(path)

    async with aiosqlite.connect(path) as db:
        rows = await db.execute_fetchall(
            f"SELECT {DIAGNOSIS_RECORD_COLUMNS} FROM diagnosis_records WHERE id = ?",
            (record_id,),
        )

    if not rows:
        return None

    return _row_to_diagnosis_record(rows[0])


def _build_stats_filters(
    *,
    since: str,
    thread_id: str | None,
    user_id: str | None,
) -> tuple[str, list[str]]:
    filters = ["created_at >= ?"]
    params = [since]

    if thread_id is not None:
        filters.append("thread_id = ?")
        params.append(thread_id)

    if user_id is not None:
        filters.append("user_id = ?")
        params.append(user_id)

    return " WHERE " + " AND ".join(filters), params


async def get_diagnosis_stats(
    *,
    days: int = 7,
    thread_id: str | None = None,
    user_id: str | None = None,
    db_path: str | None = None,
) -> DiagnosisStats:
    path = db_path or settings.SQLITE_DB_PATH
    await init_diagnosis_store(path)

    safe_days = max(days, 1)
    since = (datetime.now(UTC) - timedelta(days=safe_days - 1)).date().isoformat()
    where_clause, params = _build_stats_filters(
        since=since,
        thread_id=thread_id,
        user_id=user_id,
    )

    async with aiosqlite.connect(path) as db:
        total_rows = await db.execute_fetchall(
            f"SELECT COUNT(*) FROM diagnosis_records{where_clause}",
            params,
        )
        fault_type_rows = await db.execute_fetchall(
            f"""
            SELECT fault_type, COUNT(*)
            FROM diagnosis_records
            {where_clause}
            GROUP BY fault_type
            ORDER BY COUNT(*) DESC, fault_type ASC
            """,
            params,
        )
        severity_rows = await db.execute_fetchall(
            f"""
            SELECT severity, COUNT(*)
            FROM diagnosis_records
            {where_clause}
            GROUP BY severity
            ORDER BY COUNT(*) DESC, severity ASC
            """,
            params,
        )
        daily_rows = await db.execute_fetchall(
            f"""
            SELECT date(created_at), COUNT(*)
            FROM diagnosis_records
            {where_clause}
            GROUP BY date(created_at)
            ORDER BY date(created_at) ASC
            """,
            params,
        )

    return DiagnosisStats(
        total=total_rows[0][0],
        by_fault_type={row[0]: row[1] for row in fault_type_rows},
        by_severity={row[0]: row[1] for row in severity_rows},
        daily_counts=[DiagnosisDailyCount(date=row[0], count=row[1]) for row in daily_rows],
    )
