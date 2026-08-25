import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.logmind_eval import (  # noqa: E402
    evaluate_logmind_cases,
    evaluate_logmind_golden_replay_cases,
    evaluate_logmind_rag_cases,
    evaluate_logmind_report_cases,
    load_logmind_eval_cases,
    load_logmind_golden_replay_cases,
    load_logmind_rag_eval_cases,
    load_logmind_report_eval_cases,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate LogMind diagnostic classification cases.")
    parser.add_argument(
        "--cases",
        type=Path,
        default=ROOT_DIR / "tests" / "fixtures" / "logmind_eval_cases.json",
        help="Path to LogMind eval cases JSON.",
    )
    parser.add_argument(
        "--report-cases",
        type=Path,
        default=ROOT_DIR / "tests" / "fixtures" / "logmind_report_eval_cases.json",
        help="Path to LogMind report eval cases JSON.",
    )
    parser.add_argument(
        "--golden-cases",
        type=Path,
        default=ROOT_DIR / "tests" / "fixtures" / "logmind_golden_replay_cases.json",
        help="Path to LogMind golden replay cases JSON.",
    )
    parser.add_argument(
        "--rag-cases",
        type=Path,
        default=ROOT_DIR / "tests" / "fixtures" / "logmind_rag_eval_cases.json",
        help="Path to LogMind RAG retrieval eval cases JSON.",
    )
    parser.add_argument(
        "--public-log-cases",
        type=Path,
        default=ROOT_DIR / "tests" / "fixtures" / "logmind_public_log_eval_cases.json",
        help="Path to public log small-sample eval cases JSON.",
    )
    parser.add_argument(
        "--external-cases",
        type=Path,
        default=ROOT_DIR / "tests" / "fixtures" / "logmind_external_annotated_cases.json",
        help="Path to externally sourced annotated eval cases JSON.",
    )
    args = parser.parse_args()

    cases = load_logmind_eval_cases(args.cases)
    summary = evaluate_logmind_cases(cases)
    report_cases = load_logmind_report_eval_cases(args.report_cases)
    report_summary = evaluate_logmind_report_cases(report_cases)
    golden_cases = load_logmind_golden_replay_cases(args.golden_cases)
    golden_summary = evaluate_logmind_golden_replay_cases(golden_cases)
    rag_cases = load_logmind_rag_eval_cases(args.rag_cases)
    rag_summary = evaluate_logmind_rag_cases(rag_cases)
    public_log_cases = load_logmind_eval_cases(args.public_log_cases)
    public_log_summary = evaluate_logmind_cases(public_log_cases)
    external_cases = load_logmind_eval_cases(args.external_cases)
    external_summary = evaluate_logmind_cases(external_cases)

    print(
        f"LogMind eval: {summary.passed}/{summary.total} passed "
        f"({summary.pass_rate:.1%}), failed={summary.failed}"
    )
    for result in summary.results:
        status = "PASS" if result.passed else "FAIL"
        print(
            f"[{status}] {result.case_id}: "
            f"expected={result.expected_fault_type.value}, "
            f"predicted={result.predicted_fault_type.value}"
        )
        for issue in result.issues:
            print(f"  - {issue}")

    print(
        f"LogMind report eval: {report_summary.passed}/{report_summary.total} passed "
        f"({report_summary.pass_rate:.1%}), failed={report_summary.failed}"
    )
    print(
        "LogMind report metrics: "
        f"average_quality_score={report_summary.average_quality_score:.1f}, "
        f"structure_complete_rate={report_summary.structure_complete_rate:.1%}, "
        f"evidence_coverage_rate={report_summary.evidence_coverage_rate:.1%}, "
        f"reference_accuracy={report_summary.reference_accuracy_pass_rate:.1%}, "
        f"fact_consistency={report_summary.fact_consistency_pass_rate:.1%}"
    )
    for result in report_summary.results:
        status = "PASS" if result.passed else "FAIL"
        print(
            f"[{status}] {result.case_id}: "
            f"severity={result.parsed_severity.value}, "
            f"expected_min={result.expected_min_severity.value}, "
            f"quality_score={result.quality_score}, "
            f"reference_accuracy={result.reference_accuracy_passed}, "
            f"fact_consistency={result.fact_consistency_passed}"
        )
        for issue in result.issues:
            print(f"  - {issue}")

    print(
        f"LogMind golden replay: {golden_summary.passed}/{golden_summary.total} passed "
        f"({golden_summary.pass_rate:.1%}), failed={golden_summary.failed}"
    )
    for result in golden_summary.results:
        status = "PASS" if result.passed else "FAIL"
        print(
            f"[{status}] {result.case_id}: "
            f"quality_score={result.quality_score}, "
            f"expected_min={result.expected_min_quality_score}"
        )
        for issue in result.issues:
            print(f"  - {issue}")

    print(
        f"LogMind RAG eval: {rag_summary.passed}/{rag_summary.total} passed "
        f"({rag_summary.pass_rate:.1%}), "
        f"average_recall={rag_summary.average_recall:.1%}, "
        f"failed={rag_summary.failed}"
    )
    for result in rag_summary.results:
        status = "PASS" if result.passed else "FAIL"
        print(
            f"[{status}] {result.case_id}: "
            f"k={result.k}, "
            f"hits={len(result.hit_titles)}/{len(result.expected_knowledge_titles)}, "
            f"retrieved={result.retrieved_titles}"
        )
        for issue in result.issues:
            print(f"  - {issue}")

    print(
        f"LogMind public log eval: {public_log_summary.passed}/{public_log_summary.total} "
        f"passed ({public_log_summary.pass_rate:.1%}), failed={public_log_summary.failed}"
    )
    for result in public_log_summary.results:
        status = "PASS" if result.passed else "FAIL"
        print(
            f"[{status}] {result.case_id}: "
            f"expected={result.expected_fault_type.value}, "
            f"predicted={result.predicted_fault_type.value}"
        )
        for issue in result.issues:
            print(f"  - {issue}")

    print(
        f"LogMind external annotated eval: "
        f"{external_summary.passed}/{external_summary.total} passed "
        f"({external_summary.pass_rate:.1%}), failed={external_summary.failed}"
    )
    for result in external_summary.results:
        status = "PASS" if result.passed else "FAIL"
        print(
            f"[{status}] {result.case_id}: "
            f"expected={result.expected_fault_type.value}, "
            f"predicted={result.predicted_fault_type.value}"
        )
        for issue in result.issues:
            print(f"  - {issue}")

    return (
        0
        if (
            summary.failed == 0
            and report_summary.failed == 0
            and golden_summary.failed == 0
            and rag_summary.failed == 0
            and public_log_summary.failed == 0
            and external_summary.failed == 0
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
