from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from logging import Logger
from time import perf_counter

from schema import AgentTraceStep

TraceMetadata = dict[str, str | int | float | bool | None]


@dataclass(frozen=True)
class LogMindToolRun[T]:
    value: T
    trace_step: AgentTraceStep


def run_sync_agent_tool[T](
    *,
    step: str,
    title: str,
    tool_name: str,
    call: Callable[[], T],
    success_detail: Callable[[T], str] | str,
    success_metadata: Callable[[T], TraceMetadata] | None = None,
    fallback: T | None = None,
    failure_detail: str | None = None,
    logger: Logger | None = None,
    log_message: str | None = None,
) -> LogMindToolRun[T]:
    started_at = perf_counter()
    metadata: TraceMetadata = {"tool_name": tool_name}

    try:
        value = call()
        status = "success"
        detail = success_detail(value) if callable(success_detail) else success_detail
        if success_metadata is not None:
            metadata.update(success_metadata(value))
    except Exception as exc:
        if fallback is None:
            raise
        value = fallback
        status = "failed"
        detail = failure_detail or f"{title}失败，已降级继续执行。"
        metadata["error_type"] = type(exc).__name__
        if logger is not None:
            logger.warning(log_message or detail, exc_info=True)

    metadata["tool_latency_ms"] = round((perf_counter() - started_at) * 1000, 2)
    return LogMindToolRun(
        value=value,
        trace_step=AgentTraceStep(
            step=step,
            title=title,
            status=status,
            detail=detail,
            metadata=metadata,
        ),
    )


async def run_async_agent_tool[T](
    *,
    step: str,
    title: str,
    tool_name: str,
    call: Callable[[], Awaitable[T]],
    success_detail: Callable[[T], str] | str,
    success_metadata: Callable[[T], TraceMetadata] | None = None,
    fallback: T | None = None,
    failure_detail: str | None = None,
    logger: Logger | None = None,
    log_message: str | None = None,
) -> LogMindToolRun[T]:
    started_at = perf_counter()
    metadata: TraceMetadata = {"tool_name": tool_name}

    try:
        value = await call()
        status = "success"
        detail = success_detail(value) if callable(success_detail) else success_detail
        if success_metadata is not None:
            metadata.update(success_metadata(value))
    except Exception as exc:
        if fallback is None:
            raise
        value = fallback
        status = "failed"
        detail = failure_detail or f"{title}失败，已降级继续执行。"
        metadata["error_type"] = type(exc).__name__
        if logger is not None:
            logger.warning(log_message or detail, exc_info=True)

    metadata["tool_latency_ms"] = round((perf_counter() - started_at) * 1000, 2)
    return LogMindToolRun(
        value=value,
        trace_step=AgentTraceStep(
            step=step,
            title=title,
            status=status,
            detail=detail,
            metadata=metadata,
        ),
    )
