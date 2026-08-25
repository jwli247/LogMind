import pytest

from core.chat_store import list_chat_threads, upsert_chat_thread


@pytest.mark.asyncio
async def test_list_chat_threads_returns_recent_threads_first(tmp_path) -> None:
    db_path = tmp_path / "chat.db"

    await upsert_chat_thread(
        thread_id="thread-a",
        user_id="user-a",
        agent_id="logmind",
        message="第一次诊断：端口 8080 被占用",
        db_path=str(db_path),
    )
    await upsert_chat_thread(
        thread_id="thread-b",
        user_id="user-a",
        agent_id="logmind",
        message="第二次诊断：Redis 连接失败",
        db_path=str(db_path),
    )

    records = await list_chat_threads(
        user_id="user-a",
        agent_id="logmind",
        db_path=str(db_path),
    )

    assert [record.thread_id for record in records] == ["thread-b", "thread-a"]
    assert records[0].title == "第二次诊断：Redis 连接失败"
    assert records[0].last_message_summary == "第二次诊断：Redis 连接失败"


@pytest.mark.asyncio
async def test_upsert_chat_thread_updates_existing_thread(tmp_path) -> None:
    db_path = tmp_path / "chat.db"

    await upsert_chat_thread(
        thread_id="thread-a",
        user_id="user-a",
        agent_id="logmind",
        message="第一次问题描述",
        db_path=str(db_path),
    )
    await upsert_chat_thread(
        thread_id="thread-a",
        user_id="user-a",
        agent_id="logmind",
        message="补充新的日志内容",
        db_path=str(db_path),
    )

    records = await list_chat_threads(db_path=str(db_path))

    assert len(records) == 1
    assert records[0].title == "第一次问题描述"
    assert records[0].last_message_summary == "补充新的日志内容"


@pytest.mark.asyncio
async def test_list_chat_threads_filters_by_user_and_agent(tmp_path) -> None:
    db_path = tmp_path / "chat.db"

    await upsert_chat_thread(
        thread_id="thread-a",
        user_id="user-a",
        agent_id="logmind",
        message="LogMind 对话",
        db_path=str(db_path),
    )
    await upsert_chat_thread(
        thread_id="thread-b",
        user_id="user-b",
        agent_id="logmind",
        message="其他用户对话",
        db_path=str(db_path),
    )
    await upsert_chat_thread(
        thread_id="thread-c",
        user_id="user-a",
        agent_id="chatbot",
        message="其他 Agent 对话",
        db_path=str(db_path),
    )

    records = await list_chat_threads(
        user_id="user-a",
        agent_id="logmind",
        db_path=str(db_path),
    )

    assert len(records) == 1
    assert records[0].thread_id == "thread-a"
