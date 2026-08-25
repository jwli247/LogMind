import logging

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agents import logmind as logmind_module
from schema import FaultType, KnowledgeRef, Severity, SimilarIncidentRef


def test_retrieve_knowledge_safely_returns_refs(monkeypatch) -> None:
    knowledge_ref = KnowledgeRef(
        title="Port conflict guide",
        source="docs/knowledge/port_conflict.md",
        snippet="Port 8080 is already in use.",
    )

    def fake_retrieve_knowledge(query, *, fault_type, k):
        assert query == "port 8080 already in use"
        assert fault_type == FaultType.PORT_CONFLICT
        assert k == 3
        return [knowledge_ref]

    monkeypatch.setattr(logmind_module, "retrieve_knowledge", fake_retrieve_knowledge)

    refs = logmind_module._retrieve_knowledge_safely(
        "port 8080 already in use",
        fault_type=FaultType.PORT_CONFLICT,
        k=3,
    )

    assert refs == [knowledge_ref]


def test_retrieve_knowledge_safely_falls_back_to_empty_refs(monkeypatch, caplog) -> None:
    def fake_retrieve_knowledge(query, *, fault_type, k):
        raise RuntimeError("chroma is unavailable")

    monkeypatch.setattr(logmind_module, "retrieve_knowledge", fake_retrieve_knowledge)

    with caplog.at_level(logging.WARNING, logger="agents.logmind"):
        refs = logmind_module._retrieve_knowledge_safely(
            "port 8080 already in use",
            fault_type=FaultType.PORT_CONFLICT,
            k=3,
        )

    assert refs == []
    assert "Knowledge retrieval failed; continuing without references." in caplog.text


def test_diagnosis_output_contract_keeps_parser_sections() -> None:
    contract = logmind_module.DIAGNOSIS_OUTPUT_CONTRACT

    for heading in [
        "## 1. 问题概述",
        "## 2. 关键信息提取",
        "## 3. 可能原因分析",
        "## 4. 建议排查步骤",
        "## 5. 修复建议",
        "## 6. 后续预防建议",
        "## 7. 参考知识",
    ]:
        assert heading in contract

    for overview_label in [
        "- 故障类型：",
        "- 严重等级：",
        "- 影响组件：",
        "- 简要说明：",
    ]:
        assert overview_label in contract


def test_diagnostic_system_prompt_uses_output_contract() -> None:
    prompt = logmind_module._build_diagnostic_system_prompt(
        fault_type=FaultType.PORT_CONFLICT,
        knowledge_context="知识片段",
        similar_incident_context="历史案例",
    )

    assert "port_conflict" in prompt
    assert "知识片段" in prompt
    assert "历史案例" in prompt
    assert logmind_module.DIAGNOSIS_OUTPUT_CONTRACT in prompt


def test_format_similar_incidents_returns_context() -> None:
    incident = SimilarIncidentRef(
        record_id="record-1",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.HIGH,
        summary="历史端口冲突案例",
        created_at="2026-07-31T10:00:00+00:00",
    )

    context = logmind_module._format_similar_incidents([incident])

    assert "历史端口冲突案例" in context
    assert "record-1" in context
    assert "port_conflict" in context


@pytest.mark.asyncio
async def test_retrieve_similar_incidents_safely_falls_back_to_empty_refs(
    monkeypatch, caplog
) -> None:
    async def fake_list_similar_diagnosis_records(**kwargs):
        raise RuntimeError("sqlite unavailable")

    monkeypatch.setattr(
        logmind_module,
        "list_similar_diagnosis_records",
        fake_list_similar_diagnosis_records,
    )

    with caplog.at_level(logging.WARNING, logger="agents.logmind"):
        incidents = await logmind_module._retrieve_similar_incidents_safely(
            fault_type=FaultType.PORT_CONFLICT,
            user_id="user-1",
            thread_id="thread-1",
            limit=3,
        )

    assert incidents == []
    assert "Similar incident retrieval failed; continuing without history." in caplog.text


def test_trace_step_builds_agent_trace_step() -> None:
    step = logmind_module._trace_step(
        "knowledge_retrieval",
        "知识库检索",
        detail="检索到 2 条参考知识。",
        metadata={"hit_count": 2},
    )

    assert step.step == "knowledge_retrieval"
    assert step.title == "知识库检索"
    assert step.status == "success"
    assert step.detail == "检索到 2 条参考知识。"
    assert step.metadata == {"hit_count": 2}


def test_extract_token_usage_from_usage_metadata() -> None:
    message = AIMessage(
        content="诊断报告",
        usage_metadata={
            "input_tokens": 120,
            "output_tokens": 80,
            "total_tokens": 200,
        },
    )

    assert logmind_module._extract_token_usage(message) == {
        "input_tokens": 120,
        "output_tokens": 80,
        "total_tokens": 200,
    }


def test_extract_token_usage_from_response_metadata_token_usage() -> None:
    message = AIMessage(
        content="诊断报告",
        response_metadata={
            "token_usage": {
                "prompt_tokens": 120,
                "completion_tokens": 80,
            }
        },
    )

    assert logmind_module._extract_token_usage(message) == {
        "input_tokens": 120,
        "output_tokens": 80,
        "total_tokens": 200,
    }


def test_estimate_token_cost_uses_configured_prices(monkeypatch) -> None:
    monkeypatch.setattr(logmind_module.settings, "LOGMIND_INPUT_TOKEN_PRICE_PER_1M_USD", 0.1)
    monkeypatch.setattr(logmind_module.settings, "LOGMIND_OUTPUT_TOKEN_PRICE_PER_1M_USD", 0.4)

    cost = logmind_module._estimate_token_cost_usd(
        {
            "input_tokens": 1000,
            "output_tokens": 500,
            "total_tokens": 1500,
        }
    )

    assert cost == 0.0003


def test_evaluate_diagnosis_quality_returns_quality_metadata() -> None:
    knowledge_ref = KnowledgeRef(
        title="端口冲突排查手册",
        source="docs/knowledge/port_conflict.md",
        snippet="确认端口占用。",
    )
    report_markdown = """## 1. 问题概述
- 故障类型：端口冲突
- 严重等级：中
- 影响组件：Spring Boot Web Server
- 简要说明：Web 服务启动失败，8080 端口已被占用。

## 2. 关键信息提取
- Port 8080 was already in use.

## 3. 可能原因分析
- 端口被其他进程占用。

## 4. 建议排查步骤
- 执行 netstat 查看端口占用。

## 5. 修复建议
- 停止占用端口的进程。

## 6. 后续预防建议
- 规划服务端口。

## 7. 参考知识
- 端口冲突排查手册：确认端口占用后再处理。
"""

    quality_evaluation = logmind_module._evaluate_diagnosis_quality(
        report_markdown=report_markdown,
        input_summary="Web server failed to start. Port 8080 was already in use.",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.MEDIUM,
        key_evidence=["Port 8080"],
        knowledge_refs=[knowledge_ref],
    )

    assert quality_evaluation.quality_score == 100
    assert quality_evaluation.reference_accuracy_passed
    assert quality_evaluation.cited_knowledge_titles == ["端口冲突排查手册"]


def test_sanitize_message_redacts_string_content() -> None:
    message = HumanMessage(content="password=abc123 token=secret-token host=10.0.0.1")

    sanitized = logmind_module._sanitize_message(message)

    assert sanitized is not message
    assert "abc123" not in str(sanitized.content)
    assert "secret-token" not in str(sanitized.content)
    assert "10.0.0.1" not in str(sanitized.content)
    assert "[REDACTED_PASSWORD]" in str(sanitized.content)
    assert "[REDACTED_TOKEN]" in str(sanitized.content)
    assert "[REDACTED_IP]" in str(sanitized.content)


def test_sanitize_messages_keeps_original_message_when_unchanged() -> None:
    message = HumanMessage(content="port 8080 already in use")

    sanitized_messages = logmind_module._sanitize_messages([message])

    assert sanitized_messages == [message]
    assert sanitized_messages[0] is message
