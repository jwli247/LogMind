import json
from unittest.mock import AsyncMock, patch

import langsmith
import pytest
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langgraph.types import Interrupt, StateSnapshot

from agents.agents import Agent
from core.chat_store import upsert_chat_thread
from core.diagnosis_store import save_diagnosis_record
from schema import (
    AgentTraceStep,
    ChatHistory,
    ChatMessage,
    DiagnosisQualityEvaluation,
    FaultType,
    KnowledgeRef,
    ServiceMetadata,
    Severity,
    SimilarIncidentRef,
)
from schema.models import OpenAIModelName


def test_invoke(test_client, mock_agent) -> None:
    QUESTION = "What is the weather in Tokyo?"
    ANSWER = "The weather in Tokyo is 70 degrees."
    mock_agent.ainvoke.return_value = [("values", {"messages": [AIMessage(content=ANSWER)]})]

    response = test_client.post("/invoke", json={"message": QUESTION})
    assert response.status_code == 200

    mock_agent.ainvoke.assert_awaited_once()
    input_message = mock_agent.ainvoke.await_args.kwargs["input"]["messages"][0]
    assert input_message.content == QUESTION

    output = ChatMessage.model_validate(response.json())
    assert output.type == "ai"
    assert output.content == ANSWER


def test_invoke_custom_agent(test_client, mock_agent) -> None:
    """Test that /invoke works with a custom agent_id path parameter."""
    CUSTOM_AGENT = "custom_agent"
    QUESTION = "What is the weather in Tokyo?"
    CUSTOM_ANSWER = "The weather in Tokyo is sunny."
    DEFAULT_ANSWER = "This is from the default agent."

    # Create a separate mock for the default agent
    default_mock = AsyncMock()
    default_mock.ainvoke.return_value = [
        ("values", {"messages": [AIMessage(content=DEFAULT_ANSWER)]})
    ]

    # Configure our custom mock agent
    mock_agent.ainvoke.return_value = [("values", {"messages": [AIMessage(content=CUSTOM_ANSWER)]})]

    # Patch get_agent to return the correct agent based on the provided agent_id
    def agent_lookup(agent_id):
        if agent_id == CUSTOM_AGENT:
            return mock_agent
        return default_mock

    with patch("service.service.get_agent", side_effect=agent_lookup):
        response = test_client.post(f"/{CUSTOM_AGENT}/invoke", json={"message": QUESTION})
        assert response.status_code == 200

        # Verify custom agent was called and default wasn't
        mock_agent.ainvoke.assert_awaited_once()
        default_mock.ainvoke.assert_not_awaited()

        input_message = mock_agent.ainvoke.await_args.kwargs["input"]["messages"][0]
        assert input_message.content == QUESTION

        output = ChatMessage.model_validate(response.json())
        assert output.type == "ai"
        assert output.content == CUSTOM_ANSWER  # Verify we got the custom agent's response


def test_invoke_model_param(test_client, mock_agent) -> None:
    """Test that the model parameter is correctly passed to the agent if specified."""
    QUESTION = "What is the weather in Tokyo?"
    ANSWER = "The weather in Tokyo is sunny."
    CUSTOM_MODEL = "claude-sonnet-4-5"
    mock_agent.ainvoke.return_value = [("values", {"messages": [AIMessage(content=ANSWER)]})]

    response = test_client.post("/invoke", json={"message": QUESTION, "model": CUSTOM_MODEL})
    assert response.status_code == 200

    # Verify the model was passed correctly in the config
    mock_agent.ainvoke.assert_awaited_once()
    config = mock_agent.ainvoke.await_args.kwargs["config"]
    assert config["configurable"]["model"] == CUSTOM_MODEL

    # Verify the response is still correct
    output = ChatMessage.model_validate(response.json())
    assert output.type == "ai"
    assert output.content == ANSWER

    # Verify an invalid model throws a validation error
    INVALID_MODEL = "gpt-7-notreal"
    response = test_client.post("/invoke", json={"message": QUESTION, "model": INVALID_MODEL})
    assert response.status_code == 422


def test_invoke_no_model_param_uses_none_default(test_client, mock_agent) -> None:
    """Test that when no model is specified, UserInput defaults to None and isn't passed to the runnable config (not hardcoded gpt-5-nano)."""
    QUESTION = "What is the weather in Tokyo?"
    ANSWER = "The weather in Tokyo is sunny."
    mock_agent.ainvoke.return_value = [("values", {"messages": [AIMessage(content=ANSWER)]})]

    # Don't specify model in the request
    response = test_client.post("/invoke", json={"message": QUESTION})
    assert response.status_code == 200

    mock_agent.ainvoke.assert_awaited_once()
    config = mock_agent.ainvoke.await_args.kwargs["config"]
    assert "model" not in config["configurable"]  # Should not be present when None

    # Verify the response is still correct
    output = ChatMessage.model_validate(response.json())
    assert output.type == "ai"
    assert output.content == ANSWER


def test_invoke_custom_agent_config(test_client, mock_agent) -> None:
    """Test that the agent_config parameter is correctly passed to the agent."""
    QUESTION = "What is the weather in Tokyo?"
    ANSWER = "The weather in Tokyo is sunny."
    CUSTOM_CONFIG = {"spicy_level": 0.1, "additional_param": "value_foo"}

    mock_agent.ainvoke.return_value = [("values", {"messages": [AIMessage(content=ANSWER)]})]

    response = test_client.post(
        "/invoke", json={"message": QUESTION, "agent_config": CUSTOM_CONFIG}
    )
    assert response.status_code == 200

    # Verify the agent_config was passed correctly in the config
    mock_agent.ainvoke.assert_awaited_once()
    config = mock_agent.ainvoke.await_args.kwargs["config"]
    assert config["configurable"]["spicy_level"] == 0.1
    assert config["configurable"]["additional_param"] == "value_foo"

    # Verify the response is still correct
    output = ChatMessage.model_validate(response.json())
    assert output.type == "ai"
    assert output.content == ANSWER

    # Verify a reserved key in agent_config throws a validation error
    INVALID_CONFIG = {"model": "gpt-5-nano"}
    response = test_client.post(
        "/invoke", json={"message": QUESTION, "agent_config": INVALID_CONFIG}
    )
    assert response.status_code == 422


def test_invoke_interrupt(test_client, mock_agent) -> None:
    QUESTION = "What is the weather in Tokyo?"
    ANSWER = "The weather in Tokyo is 70 degrees."
    INTERRUPT = "Confirm weather check"
    mock_agent.ainvoke.return_value = [
        ("values", {"messages": [AIMessage(content=ANSWER)]}),
        ("updates", {"__interrupt__": [Interrupt(value=INTERRUPT)]}),
    ]

    response = test_client.post("/invoke", json={"message": QUESTION})
    assert response.status_code == 200

    mock_agent.ainvoke.assert_awaited_once()
    input_message = mock_agent.ainvoke.await_args.kwargs["input"]["messages"][0]
    assert input_message.content == QUESTION

    output = ChatMessage.model_validate(response.json())
    assert output.type == "ai"
    assert output.content == INTERRUPT


@patch("service.service.LangsmithClient")
def test_feedback(mock_client: langsmith.Client, test_client) -> None:
    ls_instance = mock_client.return_value
    ls_instance.create_feedback.return_value = None
    body = {
        "run_id": "847c6285-8fc9-4560-a83f-4e6285809254",
        "key": "human-feedback-stars",
        "score": 0.8,
    }
    response = test_client.post("/feedback", json=body)
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    ls_instance.create_feedback.assert_called_once_with(
        run_id="847c6285-8fc9-4560-a83f-4e6285809254",
        key="human-feedback-stars",
        score=0.8,
    )


def test_history(test_client, mock_agent) -> None:
    QUESTION = "What is the weather in Tokyo?"
    ANSWER = "The weather in Tokyo is 70 degrees."
    user_question = HumanMessage(content=QUESTION)
    agent_response = AIMessage(content=ANSWER)
    mock_agent.aget_state.return_value = StateSnapshot(
        values={"messages": [user_question, agent_response]},
        next=(),
        config={},
        metadata=None,
        created_at=None,
        parent_config=None,
        tasks=(),
        interrupts=(),
    )

    response = test_client.post(
        "/history", json={"thread_id": "7bcc7cc1-99d7-4b1d-bdb5-e6f90ed44de6"}
    )
    assert response.status_code == 200

    output = ChatHistory.model_validate(response.json())
    assert output.messages[0].type == "human"
    assert output.messages[0].content == QUESTION
    assert output.messages[1].type == "ai"
    assert output.messages[1].content == ANSWER


def test_history_custom_agent(test_client) -> None:
    """Test that /{agent_id}/history reads the thread through the requested agent's graph."""
    CUSTOM_AGENT = "custom_agent"
    QUESTION = "What is the weather in Tokyo?"
    ANSWER = "The weather in Tokyo is 70 degrees."

    custom_snapshot = StateSnapshot(
        values={"messages": [HumanMessage(content=QUESTION), AIMessage(content=ANSWER)]},
        next=(),
        config={},
        metadata=None,
        created_at=None,
        parent_config=None,
        tasks=(),
        interrupts=(),
    )
    # The default agent's graph doesn't know about this thread, so it returns no messages.
    default_snapshot = StateSnapshot(
        values={"messages": []},
        next=(),
        config={},
        metadata=None,
        created_at=None,
        parent_config=None,
        tasks=(),
        interrupts=(),
    )

    custom_mock = AsyncMock()
    custom_mock.aget_state.return_value = custom_snapshot
    default_mock = AsyncMock()
    default_mock.aget_state.return_value = default_snapshot

    def agent_lookup(agent_id):
        if agent_id == CUSTOM_AGENT:
            return custom_mock
        return default_mock

    with patch("service.service.get_agent", side_effect=agent_lookup):
        response = test_client.post(
            f"/{CUSTOM_AGENT}/history",
            json={"thread_id": "7bcc7cc1-99d7-4b1d-bdb5-e6f90ed44de6"},
        )
        assert response.status_code == 200

        # The custom agent's graph was used, not the default one.
        custom_mock.aget_state.assert_awaited_once()
        default_mock.aget_state.assert_not_awaited()

        output = ChatHistory.model_validate(response.json())
        assert output.messages[0].type == "human"
    assert output.messages[0].content == QUESTION
    assert output.messages[1].type == "ai"
    assert output.messages[1].content == ANSWER


@pytest.mark.asyncio
async def test_chat_threads_returns_recent_threads(test_client, monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "chat.db"
    monkeypatch.setattr("core.chat_store.settings.SQLITE_DB_PATH", str(db_path))

    await upsert_chat_thread(
        thread_id="thread-a",
        user_id="user-a",
        agent_id="logmind",
        message="端口冲突诊断",
    )
    await upsert_chat_thread(
        thread_id="thread-b",
        user_id="user-b",
        agent_id="logmind",
        message="其他用户对话",
    )
    await upsert_chat_thread(
        thread_id="thread-c",
        user_id="user-a",
        agent_id="chatbot",
        message="其他 Agent 对话",
    )

    response = test_client.get(
        "/chat/threads",
        params={"user_id": "user-a", "agent_id": "logmind"},
    )

    assert response.status_code == 200
    records = response.json()
    assert len(records) == 1
    assert records[0]["thread_id"] == "thread-a"
    assert records[0]["title"] == "端口冲突诊断"


@pytest.mark.asyncio
async def test_diagnosis_history_returns_knowledge_refs(test_client, monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "diagnosis.db"
    monkeypatch.setattr("core.diagnosis_store.settings.SQLITE_DB_PATH", str(db_path))
    knowledge_ref = KnowledgeRef(
        title="Port conflict guide",
        source="docs/knowledge/port_conflict.md",
        snippet="Find and stop the process that is already listening on the port.",
    )

    record_id = await save_diagnosis_record(
        input_summary="Web server failed to start. Port 8080 was already in use.",
        report_markdown="## Diagnosis\nPort 8080 is already occupied.",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.MEDIUM,
        thread_id="thread-knowledge",
        user_id="user-knowledge",
        model="openai-compatible",
        knowledge_refs=[knowledge_ref],
        affected_component="Spring Boot Web Server",
        key_evidence=["Port 8080 was already in use."],
        possible_causes=["Another process is listening on 8080."],
        troubleshooting_steps=["Run netstat to find the process."],
        fix_suggestions=["Stop the process or change server.port."],
        prevention_suggestions=["Reserve ports for local services."],
        confidence=0.8,
    )

    response = test_client.get("/diagnosis/history", params={"limit": 5})

    assert response.status_code == 200
    records = response.json()
    assert records[0]["id"] == record_id
    assert records[0]["knowledge_refs"] == [knowledge_ref.model_dump(mode="json")]
    assert records[0]["affected_component"] == "Spring Boot Web Server"
    assert records[0]["key_evidence"] == ["Port 8080 was already in use."]
    assert records[0]["possible_causes"] == ["Another process is listening on 8080."]
    assert records[0]["troubleshooting_steps"] == ["Run netstat to find the process."]
    assert records[0]["fix_suggestions"] == ["Stop the process or change server.port."]
    assert records[0]["prevention_suggestions"] == ["Reserve ports for local services."]
    assert records[0]["confidence"] == 0.8


@pytest.mark.asyncio
async def test_diagnosis_history_filters_by_thread_and_user(test_client, monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "diagnosis.db"
    monkeypatch.setattr("core.diagnosis_store.settings.SQLITE_DB_PATH", str(db_path))

    matching_id = await save_diagnosis_record(
        input_summary="matching diagnosis",
        report_markdown="matching report",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.MEDIUM,
        thread_id="thread-a",
        user_id="user-a",
    )
    await save_diagnosis_record(
        input_summary="same thread different user",
        report_markdown="other report",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.MEDIUM,
        thread_id="thread-a",
        user_id="user-b",
    )
    await save_diagnosis_record(
        input_summary="same user different thread",
        report_markdown="other report",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.MEDIUM,
        thread_id="thread-b",
        user_id="user-a",
    )

    response = test_client.get(
        "/diagnosis/history",
        params={"thread_id": "thread-a", "user_id": "user-a"},
    )

    assert response.status_code == 200
    records = response.json()
    assert [record["id"] for record in records] == [matching_id]


@pytest.mark.asyncio
async def test_diagnosis_stats_returns_aggregates(test_client, monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "diagnosis.db"
    monkeypatch.setattr("core.diagnosis_store.settings.SQLITE_DB_PATH", str(db_path))

    await save_diagnosis_record(
        input_summary="port diagnosis",
        report_markdown="port report",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.MEDIUM,
        thread_id="thread-a",
        user_id="user-a",
    )
    await save_diagnosis_record(
        input_summary="second port diagnosis",
        report_markdown="second port report",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.HIGH,
        thread_id="thread-a",
        user_id="user-a",
    )
    await save_diagnosis_record(
        input_summary="redis diagnosis",
        report_markdown="redis report",
        fault_type=FaultType.REDIS_CONNECTION,
        severity=Severity.HIGH,
        thread_id="thread-b",
        user_id="user-b",
    )

    response = test_client.get("/diagnosis/stats", params={"days": 7})

    assert response.status_code == 200
    stats = response.json()
    assert stats["total"] == 3
    assert stats["by_fault_type"] == {
        "port_conflict": 2,
        "redis_connection": 1,
    }
    assert stats["by_severity"] == {
        "high": 2,
        "medium": 1,
    }
    assert sum(day["count"] for day in stats["daily_counts"]) == 3


@pytest.mark.asyncio
async def test_diagnosis_stats_filters_by_thread_and_user(test_client, monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "diagnosis.db"
    monkeypatch.setattr("core.diagnosis_store.settings.SQLITE_DB_PATH", str(db_path))

    await save_diagnosis_record(
        input_summary="matching diagnosis",
        report_markdown="matching report",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.MEDIUM,
        thread_id="thread-a",
        user_id="user-a",
    )
    await save_diagnosis_record(
        input_summary="same thread different user",
        report_markdown="other report",
        fault_type=FaultType.REDIS_CONNECTION,
        severity=Severity.HIGH,
        thread_id="thread-a",
        user_id="user-b",
    )
    await save_diagnosis_record(
        input_summary="same user different thread",
        report_markdown="other report",
        fault_type=FaultType.CONFIGURATION_ERROR,
        severity=Severity.LOW,
        thread_id="thread-b",
        user_id="user-a",
    )

    response = test_client.get(
        "/diagnosis/stats",
        params={"days": 7, "thread_id": "thread-a", "user_id": "user-a"},
    )

    assert response.status_code == 200
    stats = response.json()
    assert stats["total"] == 1
    assert stats["by_fault_type"] == {"port_conflict": 1}
    assert stats["by_severity"] == {"medium": 1}


@pytest.mark.asyncio
async def test_diagnosis_observability_returns_agent_run_summary(
    test_client,
    monkeypatch,
    tmp_path,
) -> None:
    db_path = tmp_path / "diagnosis.db"
    monkeypatch.setattr("core.diagnosis_store.settings.SQLITE_DB_PATH", str(db_path))

    await save_diagnosis_record(
        input_summary="port diagnosis",
        report_markdown="port report",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.MEDIUM,
        thread_id="thread-a",
        user_id="user-a",
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
        quality_evaluation=DiagnosisQualityEvaluation(
            quality_score=91,
            quality_breakdown={"sections": 20},
            reference_accuracy_passed=True,
        ),
        agent_trace=[
            AgentTraceStep(step="intent_detection", title="诊断请求识别"),
            AgentTraceStep(
                step="report_generation",
                title="诊断报告生成",
                metadata={
                    "model_latency_ms": 900.0,
                    "input_tokens": 800,
                    "output_tokens": 400,
                    "total_tokens": 1200,
                    "estimated_cost_usd": 0.0008,
                },
            ),
            AgentTraceStep(step="knowledge_retrieval", title="知识库检索"),
            AgentTraceStep(
                step="diagnosis_record_save",
                title="诊断记录保存",
                metadata={"runtime_ms": 1300.0},
            ),
        ],
    )
    await save_diagnosis_record(
        input_summary="redis diagnosis",
        report_markdown="redis report",
        fault_type=FaultType.REDIS_CONNECTION,
        severity=Severity.HIGH,
        thread_id="thread-b",
        user_id="user-b",
        quality_evaluation=DiagnosisQualityEvaluation(
            quality_score=70,
            quality_breakdown={"sections": 10},
            reference_accuracy_passed=False,
            unsupported_knowledge_titles=["不存在的手册"],
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
    )

    response = test_client.get(
        "/diagnosis/observability",
        params={"user_id": "user-a", "thread_id": "thread-a", "fault_type": "port_conflict"},
    )

    assert response.status_code == 200
    summary = response.json()
    assert summary["total_records"] == 1
    assert summary["records_with_trace"] == 1
    assert summary["trace_coverage_rate"] == 1.0
    assert summary["knowledge_hit_rate"] == 1.0
    assert summary["similar_incident_hit_rate"] == 1.0
    assert summary["quality_evaluated_records"] == 1
    assert summary["average_quality_score"] == 91.0
    assert summary["average_runtime_ms"] == 1300.0
    assert summary["p95_runtime_ms"] == 1300.0
    assert summary["average_model_latency_ms"] == 900.0
    assert summary["p95_model_latency_ms"] == 900.0
    assert summary["token_usage_records"] == 1
    assert summary["total_input_tokens"] == 800
    assert summary["total_output_tokens"] == 400
    assert summary["total_tokens"] == 1200
    assert summary["average_total_tokens"] == 1200.0
    assert summary["total_estimated_cost_usd"] == 0.0008
    assert summary["average_estimated_cost_usd"] == 0.0008
    assert summary["low_quality_records"] == 0
    assert summary["reference_accuracy_failed_records"] == 0
    assert summary["failed_trace_steps"] == 0
    step_stats = {step["step"]: step for step in summary["step_stats"]}
    assert step_stats["intent_detection"]["success"] == 1
    assert step_stats["report_generation"]["success"] == 1
    assert step_stats["diagnosis_record_save"]["success"] == 1


def test_diagnosis_log_file_preview_returns_diagnostic_message(test_client) -> None:
    response = test_client.post(
        "/diagnosis/log-file/preview",
        files={
            "file": (
                "app.log",
                b"ERROR password=abc123 token=secret port 8080 failed",
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    preview = response.json()
    assert preview["filename"] == "app.log"
    assert preview["truncated"] is False
    assert "abc123" not in preview["content"]
    assert "secret" not in preview["content"]
    assert "[REDACTED_PASSWORD]" in preview["content"]
    assert "[REDACTED_TOKEN]" in preview["content"]
    assert "文件名：app.log" in preview["diagnostic_message"]
    assert "日志内容：" in preview["diagnostic_message"]


def test_diagnosis_log_file_preview_rejects_unsupported_file(test_client) -> None:
    response = test_client.post(
        "/diagnosis/log-file/preview",
        files={"file": ("app.json", b'{"error": "failed"}', "application/json")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Only .log and .txt files are supported"}


@pytest.mark.asyncio
async def test_diagnosis_history_detail_returns_record(test_client, monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "diagnosis.db"
    monkeypatch.setattr("core.diagnosis_store.settings.SQLITE_DB_PATH", str(db_path))

    record_id = await save_diagnosis_record(
        input_summary="detail diagnosis",
        report_markdown="detail report",
        fault_type=FaultType.CONFIGURATION_ERROR,
        severity=Severity.HIGH,
        thread_id="thread-detail",
        user_id="user-detail",
    )

    response = test_client.get(f"/diagnosis/history/{record_id}")

    assert response.status_code == 200
    record = response.json()
    assert record["id"] == record_id
    assert record["thread_id"] == "thread-detail"
    assert record["user_id"] == "user-detail"


@pytest.mark.asyncio
async def test_diagnosis_history_detail_rejects_other_user(
    test_client, monkeypatch, tmp_path
) -> None:
    db_path = tmp_path / "diagnosis.db"
    monkeypatch.setattr("core.diagnosis_store.settings.SQLITE_DB_PATH", str(db_path))

    record_id = await save_diagnosis_record(
        input_summary="detail diagnosis",
        report_markdown="detail report",
        fault_type=FaultType.CONFIGURATION_ERROR,
        severity=Severity.HIGH,
        thread_id="thread-detail",
        user_id="owner-user",
    )

    response = test_client.get(
        f"/diagnosis/history/{record_id}",
        params={"user_id": "other-user"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Diagnosis not found"}


@pytest.mark.asyncio
async def test_diagnosis_history_export_returns_markdown(test_client, monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "diagnosis.db"
    monkeypatch.setattr("core.diagnosis_store.settings.SQLITE_DB_PATH", str(db_path))

    record_id = await save_diagnosis_record(
        input_summary="export diagnosis",
        report_markdown="## 1. 问题概述\n端口冲突导致启动失败。",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.HIGH,
        thread_id="thread-export",
        user_id="user-export",
        affected_component="Spring Boot Web Server",
        key_evidence=["Port 8080 was already in use."],
        fix_suggestions=["Stop the process or change server.port."],
    )

    response = test_client.get(f"/diagnosis/history/{record_id}/export")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert (
        response.headers["content-disposition"]
        == f'attachment; filename="logmind-diagnosis-{record_id}.md"'
    )
    assert "# LogMind 诊断报告" in response.text
    assert f"- 记录 ID：{record_id}" in response.text
    assert "- 故障类型：port_conflict" in response.text
    assert "Port 8080 was already in use." in response.text
    assert "端口冲突导致启动失败。" in response.text


@pytest.mark.asyncio
async def test_diagnosis_history_export_rejects_other_user(
    test_client, monkeypatch, tmp_path
) -> None:
    db_path = tmp_path / "diagnosis.db"
    monkeypatch.setattr("core.diagnosis_store.settings.SQLITE_DB_PATH", str(db_path))

    record_id = await save_diagnosis_record(
        input_summary="export diagnosis",
        report_markdown="## 1. 问题概述\n端口冲突导致启动失败。",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.HIGH,
        thread_id="thread-export",
        user_id="owner-user",
    )

    response = test_client.get(
        f"/diagnosis/history/{record_id}/export",
        params={"user_id": "other-user"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Diagnosis not found"}


def test_diagnosis_history_detail_returns_404(test_client, monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "diagnosis.db"
    monkeypatch.setattr("core.diagnosis_store.settings.SQLITE_DB_PATH", str(db_path))

    response = test_client.get("/diagnosis/history/missing-record")

    assert response.status_code == 404
    assert response.json() == {"detail": "Diagnosis not found"}


def test_diagnosis_history_export_returns_404(test_client, monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "diagnosis.db"
    monkeypatch.setattr("core.diagnosis_store.settings.SQLITE_DB_PATH", str(db_path))

    response = test_client.get("/diagnosis/history/missing-record/export")

    assert response.status_code == 404
    assert response.json() == {"detail": "Diagnosis not found"}


@pytest.mark.asyncio
async def test_stream(test_client, mock_agent) -> None:
    """Test streaming tokens and messages."""
    QUESTION = "What is the weather in Tokyo?"
    TOKENS = ["The", " weather", " in", " Tokyo", " is", " sunny", "."]
    FINAL_ANSWER = "The weather in Tokyo is sunny."

    # Configure mock to use our async iterator function
    events = [
        (
            "messages",
            (
                AIMessageChunk(content=token),
                {"tags": []},
            ),
        )
        for token in TOKENS
    ] + [
        (
            "updates",
            {"chat_model": {"messages": [AIMessage(content=FINAL_ANSWER)]}},
        )
    ]

    async def mock_astream(**kwargs):
        for event in events:
            yield event

    mock_agent.astream = mock_astream

    # Make request with streaming
    with test_client.stream(
        "POST", "/stream", json={"message": QUESTION, "stream_tokens": True}
    ) as response:
        assert response.status_code == 200

        # Collect all SSE messages
        messages = []
        for line in response.iter_lines():
            if line and line.strip() != "data: [DONE]":  # Skip [DONE] message
                messages.append(json.loads(line.lstrip("data: ")))

        # Verify streamed tokens
        token_messages = [msg for msg in messages if msg["type"] == "token"]
        assert len(token_messages) == len(TOKENS)
        for i, msg in enumerate(token_messages):
            assert msg["content"] == TOKENS[i]

        # Verify final message
        final_messages = [msg for msg in messages if msg["type"] == "message"]
        assert len(final_messages) == 1
        assert final_messages[0]["content"]["content"] == FINAL_ANSWER
        assert final_messages[0]["content"]["type"] == "ai"


@pytest.mark.asyncio
async def test_stream_no_tokens(test_client, mock_agent) -> None:
    """Test streaming without tokens."""
    QUESTION = "What is the weather in Tokyo?"
    TOKENS = ["The", " weather", " in", " Tokyo", " is", " sunny", "."]
    FINAL_ANSWER = "The weather in Tokyo is sunny."

    # Configure mock to use our async iterator function
    events = [
        (
            "messages",
            (
                AIMessageChunk(content=token),
                {"tags": []},
            ),
        )
        for token in TOKENS
    ] + [
        (
            "updates",
            {"chat_model": {"messages": [AIMessage(content=FINAL_ANSWER)]}},
        )
    ]

    async def mock_astream(**kwargs):
        for event in events:
            yield event

    mock_agent.astream = mock_astream

    # Make request with streaming disabled
    with test_client.stream(
        "POST", "/stream", json={"message": QUESTION, "stream_tokens": False}
    ) as response:
        assert response.status_code == 200

        # Collect all SSE messages
        messages = []
        for line in response.iter_lines():
            if line and line.strip() != "data: [DONE]":  # Skip [DONE] message
                messages.append(json.loads(line.lstrip("data: ")))

        # Verify no token messages
        token_messages = [msg for msg in messages if msg["type"] == "token"]
        assert len(token_messages) == 0

        # Verify final message
        assert len(messages) == 1
        assert messages[0]["type"] == "message"
        assert messages[0]["content"]["content"] == FINAL_ANSWER
        assert messages[0]["content"]["type"] == "ai"


def test_stream_interrupt(test_client, mock_agent) -> None:
    QUESTION = "What is the weather in Tokyo?"
    INTERRUPT = "Confirm weather check"
    # Configure mock to use our async iterator function
    events = [
        (
            "updates",
            {"__interrupt__": [Interrupt(value=INTERRUPT)]},
        )
    ]

    async def mock_astream(**kwargs):
        for event in events:
            yield event

    mock_agent.astream = mock_astream

    # Make request with streaming disabled
    with test_client.stream(
        "POST", "/stream", json={"message": QUESTION, "stream_tokens": False}
    ) as response:
        assert response.status_code == 200

        # Collect all SSE messages
        messages = []
        for line in response.iter_lines():
            if line and line.strip() != "data: [DONE]":  # Skip [DONE] message
                messages.append(json.loads(line.lstrip("data: ")))

        # Verify interrupt message
        assert len(messages) == 1
        assert messages[0]["content"]["content"] == INTERRUPT
        assert messages[0]["content"]["type"] == "ai"


def test_info(test_client, mock_settings) -> None:
    """Test that /info returns the correct service metadata."""

    base_agent = Agent(description="A base agent.", graph=None)
    mock_settings.AUTH_SECRET = None
    mock_settings.DEFAULT_MODEL = OpenAIModelName.GPT_5_NANO
    mock_settings.AVAILABLE_MODELS = {OpenAIModelName.GPT_5_NANO, OpenAIModelName.GPT_5_MINI}
    with patch.dict("agents.agents.agents", {"base-agent": base_agent}, clear=True):
        response = test_client.get("/info")
        assert response.status_code == 200
        output = ServiceMetadata.model_validate(response.json())

    assert output.default_agent == "logmind"
    assert len(output.agents) == 1
    assert output.agents[0].key == "base-agent"
    assert output.agents[0].description == "A base agent."

    assert output.default_model == OpenAIModelName.GPT_5_NANO
    assert output.models == [OpenAIModelName.GPT_5_MINI, OpenAIModelName.GPT_5_NANO]
