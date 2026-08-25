import pytest

from core.logmind_tooling import run_async_agent_tool, run_sync_agent_tool


def test_run_sync_agent_tool_records_success_metadata() -> None:
    result = run_sync_agent_tool(
        step="fault_classification",
        title="故障类型分类",
        tool_name="classify_fault_type",
        call=lambda: "port_conflict",
        success_detail=lambda value: f"分类结果为 {value}。",
        success_metadata=lambda value: {"tool_output_summary": value},
    )

    assert result.value == "port_conflict"
    assert result.trace_step.status == "success"
    assert result.trace_step.metadata["tool_name"] == "classify_fault_type"
    assert result.trace_step.metadata["tool_output_summary"] == "port_conflict"
    assert isinstance(result.trace_step.metadata["tool_latency_ms"], float)


def test_run_sync_agent_tool_uses_fallback_and_records_failure() -> None:
    def failing_call() -> list[str]:
        raise RuntimeError("knowledge store unavailable")

    result = run_sync_agent_tool(
        step="knowledge_retrieval",
        title="知识库检索",
        tool_name="retrieve_knowledge",
        call=failing_call,
        success_detail="检索成功。",
        fallback=[],
        failure_detail="知识库检索失败，已降级为空引用继续诊断。",
    )

    assert result.value == []
    assert result.trace_step.status == "failed"
    assert result.trace_step.metadata["error_type"] == "RuntimeError"
    assert result.trace_step.metadata["tool_name"] == "retrieve_knowledge"


def test_run_sync_agent_tool_reraises_when_no_fallback_is_configured() -> None:
    with pytest.raises(ValueError, match="invalid input"):
        run_sync_agent_tool(
            step="input_sanitization",
            title="输入敏感信息脱敏",
            tool_name="sanitize_sensitive_text",
            call=lambda: (_ for _ in ()).throw(ValueError("invalid input")),
            success_detail="脱敏完成。",
        )


@pytest.mark.asyncio
async def test_run_async_agent_tool_records_success_metadata() -> None:
    async def successful_call() -> int:
        return 3

    result = await run_async_agent_tool(
        step="similar_incident_retrieval",
        title="相似历史案例检索",
        tool_name="list_similar_diagnosis_records",
        call=successful_call,
        success_detail=lambda value: f"检索到 {value} 条历史案例。",
        success_metadata=lambda value: {"hit_count": value},
    )

    assert result.value == 3
    assert result.trace_step.status == "success"
    assert result.trace_step.metadata["hit_count"] == 3
    assert isinstance(result.trace_step.metadata["tool_latency_ms"], float)
