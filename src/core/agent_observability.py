from collections import defaultdict

from schema import (
    AgentObservabilitySummary,
    AgentTraceStepStats,
    DiagnosisQualityEvaluation,
    DiagnosisRecord,
)


def build_agent_observability_summary(
    records: list[DiagnosisRecord],
) -> AgentObservabilitySummary:
    total_records = len(records)
    records_with_trace = sum(1 for record in records if record.agent_trace)
    total_trace_steps = sum(len(record.agent_trace) for record in records)
    failed_trace_records = sum(
        1
        for record in records
        if any(_is_failed_trace_status(step.status) for step in record.agent_trace)
    )
    failed_trace_steps = sum(
        1
        for record in records
        for step in record.agent_trace
        if _is_failed_trace_status(step.status)
    )
    knowledge_hit_records = sum(1 for record in records if record.knowledge_refs)
    similar_incident_hit_records = sum(1 for record in records if record.similar_incidents)
    quality_evaluations = [
        record.quality_evaluation for record in records if record.quality_evaluation is not None
    ]
    quality_evaluated_records = len(quality_evaluations)
    runtime_durations = _collect_trace_durations(records, "diagnosis_record_save", "runtime_ms")
    model_latencies = _collect_trace_durations(records, "report_generation", "model_latency_ms")
    token_metrics = _collect_token_metrics(records)
    low_quality_records = sum(
        1 for quality_evaluation in quality_evaluations if quality_evaluation.quality_score < 80
    )
    reference_accuracy_failed_records = sum(
        1
        for quality_evaluation in quality_evaluations
        if not quality_evaluation.reference_accuracy_passed
    )

    return AgentObservabilitySummary(
        total_records=total_records,
        records_with_trace=records_with_trace,
        trace_coverage_rate=_ratio(records_with_trace, total_records),
        total_trace_steps=total_trace_steps,
        average_trace_steps_per_record=_ratio(total_trace_steps, total_records),
        failed_trace_records=failed_trace_records,
        failed_trace_steps=failed_trace_steps,
        knowledge_hit_records=knowledge_hit_records,
        knowledge_hit_rate=_ratio(knowledge_hit_records, total_records),
        similar_incident_hit_records=similar_incident_hit_records,
        similar_incident_hit_rate=_ratio(similar_incident_hit_records, total_records),
        quality_evaluated_records=quality_evaluated_records,
        average_quality_score=_average_quality_score(quality_evaluations),
        average_runtime_ms=_average(runtime_durations),
        p95_runtime_ms=_percentile(runtime_durations, 0.95),
        average_model_latency_ms=_average(model_latencies),
        p95_model_latency_ms=_percentile(model_latencies, 0.95),
        token_usage_records=token_metrics["token_usage_records"],
        total_input_tokens=token_metrics["total_input_tokens"],
        total_output_tokens=token_metrics["total_output_tokens"],
        total_tokens=token_metrics["total_tokens"],
        average_total_tokens=_ratio_float(
            token_metrics["total_tokens"],
            token_metrics["token_usage_records"],
        ),
        total_estimated_cost_usd=round(token_metrics["total_estimated_cost_usd"], 8),
        average_estimated_cost_usd=_average_cost(
            token_metrics["total_estimated_cost_usd"],
            token_metrics["token_usage_records"],
        ),
        low_quality_records=low_quality_records,
        reference_accuracy_failed_records=reference_accuracy_failed_records,
        step_stats=_build_step_stats(records),
        failure_reasons=_collect_failure_reasons(records),
    )


def _build_step_stats(records: list[DiagnosisRecord]) -> list[AgentTraceStepStats]:
    stats: dict[str, dict[str, int | str]] = {}

    for record in records:
        for step in record.agent_trace:
            current = stats.setdefault(
                step.step,
                {
                    "step": step.step,
                    "title": step.title,
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "skipped": 0,
                    "other": 0,
                },
            )
            current["total"] = int(current["total"]) + 1

            status = step.status.lower()
            if status == "success":
                current["success"] = int(current["success"]) + 1
            elif status in {"failed", "failure", "error"}:
                current["failed"] = int(current["failed"]) + 1
            elif status == "skipped":
                current["skipped"] = int(current["skipped"]) + 1
            else:
                current["other"] = int(current["other"]) + 1

    return [
        AgentTraceStepStats.model_validate(step_stats)
        for step_stats in sorted(stats.values(), key=lambda item: str(item["step"]))
    ]


def _collect_failure_reasons(records: list[DiagnosisRecord]) -> list[str]:
    reason_counts: dict[str, int] = defaultdict(int)

    for record in records:
        for step in record.agent_trace:
            if not _is_failed_trace_status(step.status):
                continue

            reason = step.detail or step.title or step.step
            reason_counts[reason] += 1

    return [
        f"{reason} ({count})"
        for reason, count in sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _is_failed_trace_status(status: str) -> bool:
    return status.lower() in {"failed", "failure", "error"}


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0

    return round(numerator / denominator, 4)


def _average_quality_score(quality_evaluations: list[DiagnosisQualityEvaluation]) -> float:
    if not quality_evaluations:
        return 0.0

    return round(
        sum(quality_evaluation.quality_score for quality_evaluation in quality_evaluations)
        / len(quality_evaluations),
        2,
    )


def _collect_trace_durations(
    records: list[DiagnosisRecord],
    step_name: str,
    metadata_key: str,
) -> list[float]:
    durations: list[float] = []

    for record in records:
        for step in record.agent_trace:
            if step.step != step_name:
                continue

            value = step.metadata.get(metadata_key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                durations.append(float(value))

    return durations


def _collect_token_metrics(records: list[DiagnosisRecord]) -> dict[str, int | float]:
    token_usage_records = 0
    total_input_tokens = 0
    total_output_tokens = 0
    total_tokens = 0
    total_estimated_cost_usd = 0.0

    for record in records:
        for step in record.agent_trace:
            if step.step != "report_generation":
                continue

            input_tokens = _metadata_int(step.metadata.get("input_tokens"))
            output_tokens = _metadata_int(step.metadata.get("output_tokens"))
            current_total_tokens = _metadata_int(step.metadata.get("total_tokens"))
            estimated_cost_usd = _metadata_float(step.metadata.get("estimated_cost_usd"))
            if (
                input_tokens is None
                and output_tokens is None
                and current_total_tokens is None
                and estimated_cost_usd is None
            ):
                continue

            token_usage_records += 1
            total_input_tokens += input_tokens or 0
            total_output_tokens += output_tokens or 0
            if current_total_tokens is not None:
                total_tokens += current_total_tokens
            else:
                total_tokens += (input_tokens or 0) + (output_tokens or 0)
            total_estimated_cost_usd += estimated_cost_usd or 0.0

    return {
        "token_usage_records": token_usage_records,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_tokens": total_tokens,
        "total_estimated_cost_usd": total_estimated_cost_usd,
    }


def _metadata_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _metadata_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _average(values: list[float]) -> float:
    if not values:
        return 0.0

    return round(sum(values) / len(values), 2)


def _ratio_float(numerator: int | float, denominator: int) -> float:
    if denominator == 0:
        return 0.0

    return round(float(numerator) / denominator, 2)


def _average_cost(total_cost_usd: int | float, count: int) -> float:
    if count == 0:
        return 0.0

    return round(float(total_cost_usd) / count, 8)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0

    sorted_values = sorted(values)
    index = max(round(len(sorted_values) * percentile + 0.5) - 1, 0)
    index = min(index, len(sorted_values) - 1)
    return round(sorted_values[index], 2)
