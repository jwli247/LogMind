import argparse
import statistics
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.logmind_eval import (  # noqa: E402
    evaluate_logmind_case,
    evaluate_logmind_rag_case,
    evaluate_logmind_report_case,
    load_logmind_eval_cases,
    load_logmind_rag_eval_cases,
    load_logmind_report_eval_cases,
)


@dataclass
class BenchmarkSummary:
    name: str
    total: int
    passed: int
    durations_ms: list[float]

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def failure_rate(self) -> float:
        return self.failed / self.total if self.total else 0.0

    @property
    def average_ms(self) -> float:
        return sum(self.durations_ms) / len(self.durations_ms) if self.durations_ms else 0.0

    @property
    def p50_ms(self) -> float:
        return statistics.median(self.durations_ms) if self.durations_ms else 0.0

    @property
    def p95_ms(self) -> float:
        if not self.durations_ms:
            return 0.0
        if len(self.durations_ms) == 1:
            return self.durations_ms[0]

        return statistics.quantiles(self.durations_ms, n=20, method="inclusive")[18]


def _benchmark_cases(
    *,
    name: str,
    cases: list[Any],
    evaluator: Callable[[Any], Any],
) -> BenchmarkSummary:
    durations_ms: list[float] = []
    passed = 0

    for case in cases:
        started_at = perf_counter()
        result = evaluator(case)
        durations_ms.append((perf_counter() - started_at) * 1000)
        if result.passed:
            passed += 1

    return BenchmarkSummary(
        name=name,
        total=len(cases),
        passed=passed,
        durations_ms=durations_ms,
    )


def _print_summary(summary: BenchmarkSummary) -> None:
    print(
        f"{summary.name}: "
        f"{summary.passed}/{summary.total} passed "
        f"({summary.pass_rate:.1%}), "
        f"failure_rate={summary.failure_rate:.1%}, "
        f"average_ms={summary.average_ms:.2f}, "
        f"p50_ms={summary.p50_ms:.2f}, "
        f"p95_ms={summary.p95_ms:.2f}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark LogMind offline eval pipeline without calling a live LLM."
    )
    parser.add_argument(
        "--local-cases",
        type=Path,
        default=ROOT_DIR / "tests" / "fixtures" / "logmind_eval_cases.json",
        help="Path to local regression eval cases JSON.",
    )
    parser.add_argument(
        "--public-log-cases",
        type=Path,
        default=ROOT_DIR / "tests" / "fixtures" / "logmind_public_log_eval_cases.json",
        help="Path to public log eval cases JSON.",
    )
    parser.add_argument(
        "--external-cases",
        type=Path,
        default=ROOT_DIR / "tests" / "fixtures" / "logmind_external_annotated_cases.json",
        help="Path to external annotated eval cases JSON.",
    )
    parser.add_argument(
        "--rag-cases",
        type=Path,
        default=ROOT_DIR / "tests" / "fixtures" / "logmind_rag_eval_cases.json",
        help="Path to RAG eval cases JSON.",
    )
    parser.add_argument(
        "--report-cases",
        type=Path,
        default=ROOT_DIR / "tests" / "fixtures" / "logmind_report_eval_cases.json",
        help="Path to report eval cases JSON.",
    )
    args = parser.parse_args()

    classification_cases = [
        *load_logmind_eval_cases(args.local_cases),
        *load_logmind_eval_cases(args.public_log_cases),
        *load_logmind_eval_cases(args.external_cases),
    ]
    rag_cases = load_logmind_rag_eval_cases(args.rag_cases)
    report_cases = load_logmind_report_eval_cases(args.report_cases)

    summaries = [
        _benchmark_cases(
            name="classification_eval",
            cases=classification_cases,
            evaluator=evaluate_logmind_case,
        ),
        _benchmark_cases(
            name="rag_top3_eval",
            cases=rag_cases,
            evaluator=evaluate_logmind_rag_case,
        ),
        _benchmark_cases(
            name="report_quality_eval",
            cases=report_cases,
            evaluator=evaluate_logmind_report_case,
        ),
    ]

    print("LogMind offline pipeline benchmark")
    for summary in summaries:
        _print_summary(summary)

    total = sum(summary.total for summary in summaries)
    passed = sum(summary.passed for summary in summaries)
    durations = [
        duration
        for summary in summaries
        for duration in summary.durations_ms
    ]
    overall = BenchmarkSummary(
        name="overall_offline_eval",
        total=total,
        passed=passed,
        durations_ms=durations,
    )
    _print_summary(overall)

    return 0 if overall.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
