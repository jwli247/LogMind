import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.logmind_baseline_eval import build_logmind_baseline_comparison  # noqa: E402
from core.logmind_eval import (  # noqa: E402
    load_logmind_eval_cases,
    load_logmind_rag_eval_cases,
    load_logmind_report_eval_cases,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare LogMind baseline strategies.")
    parser.add_argument(
        "--cases",
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
        help="Path to RAG retrieval eval cases JSON.",
    )
    parser.add_argument(
        "--report-cases",
        type=Path,
        default=ROOT_DIR / "tests" / "fixtures" / "logmind_report_eval_cases.json",
        help="Path to report eval cases JSON.",
    )
    args = parser.parse_args()

    classification_cases = [
        *load_logmind_eval_cases(args.cases),
        *load_logmind_eval_cases(args.public_log_cases),
        *load_logmind_eval_cases(args.external_cases),
    ]
    comparison = build_logmind_baseline_comparison(
        classification_cases=classification_cases,
        rag_cases=load_logmind_rag_eval_cases(args.rag_cases),
        report_cases=load_logmind_report_eval_cases(args.report_cases),
    )

    print("LogMind baseline comparison")
    print(
        "strategy | classification | rag_top3 | report_eval | trace | observability"
    )
    print("-" * 78)
    for row in comparison.rows:
        print(
            " | ".join(
                [
                    row.strategy,
                    _format_count_rate(
                        row.classification_passed,
                        row.classification_total,
                        row.classification_pass_rate,
                    ),
                    _format_count_rate(
                        row.rag_passed,
                        row.rag_total,
                        row.rag_top3_recall,
                    ),
                    _format_count_rate(
                        row.report_eval_passed,
                        row.report_eval_total,
                        row.report_eval_pass_rate,
                    ),
                    "yes" if row.trace_available else "no",
                    "yes" if row.observability_available else "no",
                ]
            )
        )

    print()
    print("Notes")
    for row in comparison.rows:
        for note in row.notes:
            print(f"- {row.strategy}: {note}")

    return 0


def _format_count_rate(
    passed: int | None,
    total: int | None,
    rate: float | None,
) -> str:
    if passed is None or total is None or rate is None:
        return "-"

    return f"{passed}/{total} ({rate:.1%})"


if __name__ == "__main__":
    raise SystemExit(main())
