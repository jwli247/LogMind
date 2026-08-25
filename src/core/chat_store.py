from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

from core import settings
from schema import ChatThreadSummary

CREATE_CHAT_THREADS_TABLE = """
CREATE TABLE IF NOT EXISTS chat_threads (
    thread_id TEXT NOT NULL,
    user_id TEXT,
    agent_id TEXT NOT NULL,
    title TEXT NOT NULL,
    last_message_summary TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (agent_id, thread_id)
)
"""


async def init_chat_store(db_path: str | None = None) -> None:
    path = db_path or settings.SQLITE_DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(path) as db:
        await db.execute(CREATE_CHAT_THREADS_TABLE)
        await db.commit()


async def upsert_chat_thread(
    *,
    thread_id: str,
    agent_id: str,
    user_id: str | None = None,
    message: str,
    db_path: str | None = None,
) -> None:
    path = db_path or settings.SQLITE_DB_PATH
    now = datetime.now(UTC).isoformat()
    title = _build_title(message)
    summary = _build_summary(message)

    await init_chat_store(path)

    async with aiosqlite.connect(path) as db:
        await db.execute(
            """
            INSERT INTO chat_threads (
                thread_id, user_id, agent_id, title,
                last_message_summary, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_id, thread_id) DO UPDATE SET
                user_id = COALESCE(excluded.user_id, chat_threads.user_id),
                last_message_summary = excluded.last_message_summary,
                updated_at = excluded.updated_at
            """,
            (thread_id, user_id, agent_id, title, summary, now, now),
        )
        await db.commit()


async def list_chat_threads(
    *,
    limit: int = 20,
    user_id: str | None = None,
    agent_id: str | None = None,
    db_path: str | None = None,
) -> list[ChatThreadSummary]:
    path = db_path or settings.SQLITE_DB_PATH
    await init_chat_store(path)

    query = """
        SELECT thread_id, user_id, agent_id, title,
               last_message_summary, created_at, updated_at
        FROM chat_threads
    """
    filters: list[str] = []
    params: list[str | int] = []

    if user_id is not None:
        filters.append("user_id = ?")
        params.append(user_id)

    if agent_id is not None:
        filters.append("agent_id = ?")
        params.append(agent_id)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)

    async with aiosqlite.connect(path) as db:
        rows = await db.execute_fetchall(query, params)

    return [
        ChatThreadSummary(
            thread_id=row[0],
            user_id=row[1],
            agent_id=row[2],
            title=row[3],
            last_message_summary=row[4],
            created_at=row[5],
            updated_at=row[6],
        )
        for row in rows
    ]


def _build_title(message: str) -> str:
    summary = _build_summary(message)
    return summary[:40] or "新对话"


def _build_summary(message: str) -> str:
    normalized = " ".join(message.strip().split())
    return normalized[:120]
