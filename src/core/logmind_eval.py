import json
from pathlib import Path

from pydantic import BaseModel, Field

from core.diagnosis_parser import parse_diagnosis_markdown
from schema import FaultType, KnowledgeRef, Severity

REQUIRED_REPORT_SECTIONS: tuple[str, ...] = (
    "## 1. 问题概述",
    "## 2. 关键信息提取",
    "## 3. 可能原因分析",
    "## 4. 建议排查步骤",
    "## 5. 修复建议",
    "## 6. 后续预防建议",
    "## 7. 参考知识",
)

REPORT_QUALITY_WEIGHTS = {
    "sections": 15,
    "evidence": 15,
    "causes": 15,
    "troubleshooting": 15,
    "fixes": 15,
    "prevention": 10,
    "references": 5,
    "grounding": 10,
}


class LogMindEvalCase(BaseModel):
    id: str = Field(description="评测案例 ID")
    name: str = Field(description="评测案例名称")
    input_text: str = Field(description="用户输入的日志、异常堆栈或故障描述")
    expected_fault_type: FaultType = Field(description="期望识别出的故障类型")
    dataset: str | None = Field(default=None, description="样本来源数据集或案例集合")
    source_url: str | None = Field(default=None, description="样本来源 URL")
    annotation_note: str | None = Field(default=None, description="人工标注说明")
    expected_diagnostic_request: bool = Field(
        default=True,
        description="期望是否被识别为诊断请求",
    )
    required_input_evidence: list[str] = Field(
        default_factory=list,
        description="案例输入中必须包含的关键证据词，用于防止评测样例退化",
    )


class LogMindEvalResult(BaseModel):
    case_id: str
    name: str
    passed: bool
    predicted_fault_type: FaultType
    expected_fault_type: FaultType
    predicted_diagnostic_request: bool
    expected_diagnostic_request: bool
    issues: list[str] = Field(default_factory=list)


class LogMindEvalSummary(BaseModel):
    total: int
    passed: int
    failed: int
    pass_rate: float
    results: list[LogMindEvalResult]


class LogMindReportEvalCase(BaseModel):
    id: str = Field(description="报告评测案例 ID")
    name: str = Field(description="报告评测案例名称")
    input_summary: str = Field(description="原始用户输入摘要")
    report_markdown: str = Field(description="待评测的诊断报告 Markdown")
    expected_fault_type: FaultType = Field(description="期望故障类型")
    expected_min_severity: Severity = Field(
        default=Severity.LOW,
        description="期望最低严重等级",
    )
    required_evidence: list[str] = Field(
        default_factory=list,
        description="报告关键信息部分必须保留的证据词",
    )
    knowledge_refs: list[KnowledgeRef] = Field(
        default_factory=list,
        description="本次诊断实际检索到的知识引用",
    )
    required_grounding_terms: list[str] = Field(
        default_factory=list,
        description="原因分析和修复建议中必须能回溯到证据来源的关键术语",
    )
    min_key_evidence: int = Field(default=1, ge=0, description="最少关键证据条数")
    min_possible_causes: int = Field(default=1, ge=0, description="最少可能原因条数")
    min_troubleshooting_steps: int = Field(default=1, ge=0, description="最少排查步骤条数")
    min_fix_suggestions: int = Field(default=1, ge=0, description="最少修复建议条数")
    min_prevention_suggestions: int = Field(default=1, ge=0, description="最少预防建议条数")


class LogMindReportEvalResult(BaseModel):
    case_id: str
    name: str
    passed: bool
    parsed_severity: Severity
    expected_min_severity: Severity
    quality_score: int = Field(ge=0, le=100)
    quality_breakdown: dict[str, int] = Field(default_factory=dict)
    cited_knowledge_titles: list[str] = Field(default_factory=list)
    unsupported_knowledge_titles: list[str] = Field(default_factory=list)
    reference_accuracy_passed: bool = True
    fact_consistency_passed: bool = True
    grounded_terms: list[str] = Field(default_factory=list)
    ungrounded_terms: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class LogMindReportEvalSummary(BaseModel):
    total: int
    passed: int
    failed: int
    pass_rate: float
    average_quality_score: float
    structure_complete_rate: float
    evidence_coverage_rate: float
    reference_accuracy_pass_rate: float
    fact_consistency_pass_rate: float
    results: list[LogMindReportEvalResult]


class LogMindGoldenReplayCase(BaseModel):
    id: str = Field(description="Golden 回放案例 ID")
    name: str = Field(description="Golden 回放案例名称")
    input_text: str = Field(description="原始诊断输入")
    generated_report_markdown: str = Field(description="已保存的模型生成诊断报告")
    expected_fault_type: FaultType = Field(description="期望故障类型")
    expected_min_severity: Severity = Field(
        default=Severity.LOW,
        description="期望最低严重等级",
    )
    required_input_evidence: list[str] = Field(
        default_factory=list,
        description="输入中应保留的关键证据词",
    )
    required_report_evidence: list[str] = Field(
        default_factory=list,
        description="报告关键信息部分应保留的证据词",
    )
    knowledge_refs: list[KnowledgeRef] = Field(
        default_factory=list,
        description="回放时实际检索到的知识引用",
    )
    required_grounding_terms: list[str] = Field(
        default_factory=list,
        description="回放报告中必须能回溯到证据来源的关键术语",
    )
    expected_min_quality_score: int = Field(
        default=80,
        ge=0,
        le=100,
        description="报告最低质量分",
    )


class LogMindGoldenReplayResult(BaseModel):
    case_id: str
    name: str
    passed: bool
    input_passed: bool
    report_passed: bool
    quality_score: int
    expected_min_quality_score: int
    issues: list[str] = Field(default_factory=list)


class LogMindGoldenReplaySummary(BaseModel):
    total: int
    passed: int
    failed: int
    pass_rate: float
    results: list[LogMindGoldenReplayResult]


class LogMindRagEvalCase(BaseModel):
    id: str = Field(description="RAG 评测案例 ID")
    name: str = Field(description="RAG 评测案例名称")
    query: str = Field(description="用于检索知识库的日志、异常或排障问题")
    fault_type: FaultType | None = Field(
        default=None,
        description="可选的故障类型过滤条件",
    )
    expected_knowledge_titles: list[str] = Field(
        description="期望 Top-k 召回的知识库标题",
    )
    k: int = Field(default=3, ge=1, description="检索 Top-k")
    min_hits: int = Field(default=1, ge=1, description="最少命中标题数")


class LogMindRagEvalResult(BaseModel):
    case_id: str
    name: str
    passed: bool
    k: int
    expected_knowledge_titles: list[str]
    retrieved_titles: list[str]
    hit_titles: list[str] = Field(default_factory=list)
    recall: float
    issues: list[str] = Field(default_factory=list)


class LogMindRagEvalSummary(BaseModel):
    total: int
    passed: int
    failed: int
    pass_rate: float
    average_recall: float
    results: list[LogMindRagEvalResult]


class KnowledgeReferenceAccuracyResult(BaseModel):
    passed: bool
    cited_titles: list[str] = Field(default_factory=list)
    supported_titles: list[str] = Field(default_factory=list)
    unsupported_titles: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class FactConsistencyResult(BaseModel):
    passed: bool
    grounded_terms: list[str] = Field(default_factory=list)
    missing_from_sources: list[str] = Field(default_factory=list)
    missing_from_report: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


def load_logmind_eval_cases(path: str | Path) -> list[LogMindEvalCase]:
    raw_cases = json.loads(Path(path).read_text(encoding="utf-8"))
    return [LogMindEvalCase.model_validate(raw_case) for raw_case in raw_cases]


def load_logmind_report_eval_cases(path: str | Path) -> list[LogMindReportEvalCase]:
    raw_cases = json.loads(Path(path).read_text(encoding="utf-8"))
    return [LogMindReportEvalCase.model_validate(raw_case) for raw_case in raw_cases]


def load_logmind_golden_replay_cases(path: str | Path) -> list[LogMindGoldenReplayCase]:
    raw_cases = json.loads(Path(path).read_text(encoding="utf-8"))
    return [LogMindGoldenReplayCase.model_validate(raw_case) for raw_case in raw_cases]


def load_logmind_rag_eval_cases(path: str | Path) -> list[LogMindRagEvalCase]:
    raw_cases = json.loads(Path(path).read_text(encoding="utf-8"))
    return [LogMindRagEvalCase.model_validate(raw_case) for raw_case in raw_cases]


def evaluate_logmind_case(case: LogMindEvalCase) -> LogMindEvalResult:
    from agents.logmind_classifier import classify_fault_type, is_diagnostic_request

    predicted_diagnostic_request = is_diagnostic_request(case.input_text)
    predicted_fault_type = classify_fault_type(case.input_text)
    issues: list[str] = []

    if predicted_diagnostic_request != case.expected_diagnostic_request:
        issues.append(
            "diagnostic_request mismatch: "
            f"expected {case.expected_diagnostic_request}, got {predicted_diagnostic_request}"
        )

    if predicted_fault_type != case.expected_fault_type:
        issues.append(
            "fault_type mismatch: "
            f"expected {case.expected_fault_type.value}, got {predicted_fault_type.value}"
        )

    normalized_input = case.input_text.lower()
    missing_evidence = [
        evidence
        for evidence in case.required_input_evidence
        if evidence.lower() not in normalized_input
    ]
    if missing_evidence:
        issues.append("missing required input evidence: " + ", ".join(missing_evidence))

    return LogMindEvalResult(
        case_id=case.id,
        name=case.name,
        passed=not issues,
        predicted_fault_type=predicted_fault_type,
        expected_fault_type=case.expected_fault_type,
        predicted_diagnostic_request=predicted_diagnostic_request,
        expected_diagnostic_request=case.expected_diagnostic_request,
        issues=issues,
    )


def evaluate_logmind_report_case(case: LogMindReportEvalCase) -> LogMindReportEvalResult:
    parsed_report = parse_diagnosis_markdown(
        case.report_markdown,
        fallback_summary=case.input_summary,
        fault_type=case.expected_fault_type,
        severity=case.expected_min_severity,
    )
    issues: list[str] = []

    missing_sections = [
        section for section in REQUIRED_REPORT_SECTIONS if section not in case.report_markdown
    ]
    if missing_sections:
        issues.append("missing report sections: " + ", ".join(missing_sections))

    severity_rank = {
        Severity.LOW: 1,
        Severity.MEDIUM: 2,
        Severity.HIGH: 3,
        Severity.CRITICAL: 4,
    }
    if severity_rank[parsed_report.severity] < severity_rank[case.expected_min_severity]:
        issues.append(
            "severity lower than expected: "
            f"expected at least {case.expected_min_severity.value}, "
            f"got {parsed_report.severity.value}"
        )

    _append_min_count_issue(
        issues,
        field_name="key_evidence",
        actual=len(parsed_report.key_evidence),
        expected=case.min_key_evidence,
    )
    _append_min_count_issue(
        issues,
        field_name="possible_causes",
        actual=len(parsed_report.possible_causes),
        expected=case.min_possible_causes,
    )
    _append_min_count_issue(
        issues,
        field_name="troubleshooting_steps",
        actual=len(parsed_report.troubleshooting_steps),
        expected=case.min_troubleshooting_steps,
    )
    _append_min_count_issue(
        issues,
        field_name="fix_suggestions",
        actual=len(parsed_report.fix_suggestions),
        expected=case.min_fix_suggestions,
    )
    _append_min_count_issue(
        issues,
        field_name="prevention_suggestions",
        actual=len(parsed_report.prevention_suggestions),
        expected=case.min_prevention_suggestions,
    )

    key_evidence_text = "\n".join(parsed_report.key_evidence).lower()
    missing_evidence = [
        evidence
        for evidence in case.required_evidence
        if evidence.lower() not in key_evidence_text
    ]
    if missing_evidence:
        issues.append("missing required report evidence: " + ", ".join(missing_evidence))

    reference_accuracy = evaluate_knowledge_reference_accuracy(
        report_markdown=case.report_markdown,
        knowledge_refs=case.knowledge_refs,
    )
    issues.extend(reference_accuracy.issues)
    fact_consistency = evaluate_fact_consistency(
        report_markdown=case.report_markdown,
        input_summary=case.input_summary,
        knowledge_refs=case.knowledge_refs,
        required_grounding_terms=case.required_grounding_terms,
    )
    issues.extend(fact_consistency.issues)

    quality_breakdown = score_logmind_report_quality(
        case=case,
        missing_sections=missing_sections,
        missing_evidence=missing_evidence,
        reference_accuracy=reference_accuracy,
        fact_consistency=fact_consistency,
    )

    return LogMindReportEvalResult(
        case_id=case.id,
        name=case.name,
        passed=not issues,
        parsed_severity=parsed_report.severity,
        expected_min_severity=case.expected_min_severity,
        quality_score=sum(quality_breakdown.values()),
        quality_breakdown=quality_breakdown,
        cited_knowledge_titles=reference_accuracy.cited_titles,
        unsupported_knowledge_titles=reference_accuracy.unsupported_titles,
        reference_accuracy_passed=reference_accuracy.passed,
        fact_consistency_passed=fact_consistency.passed,
        grounded_terms=fact_consistency.grounded_terms,
        ungrounded_terms=fact_consistency.missing_from_sources,
        issues=issues,
    )


def evaluate_logmind_report_cases(
    cases: list[LogMindReportEvalCase],
) -> LogMindReportEvalSummary:
    results = [evaluate_logmind_report_case(case) for case in cases]
    passed = sum(result.passed for result in results)
    total = len(results)
    pass_rate = passed / total if total else 0.0
    average_quality_score = (
        sum(result.quality_score for result in results) / total if total else 0.0
    )
    structure_complete_rate = _report_metric_rate(
        results,
        lambda result: result.quality_breakdown.get("sections", 0)
        == REPORT_QUALITY_WEIGHTS["sections"],
    )
    evidence_coverage_rate = _report_metric_rate(
        results,
        lambda result: result.quality_breakdown.get("evidence", 0)
        == REPORT_QUALITY_WEIGHTS["evidence"],
    )
    reference_accuracy_pass_rate = _report_metric_rate(
        results,
        lambda result: result.reference_accuracy_passed,
    )
    fact_consistency_pass_rate = _report_metric_rate(
        results,
        lambda result: result.fact_consistency_passed,
    )

    return LogMindReportEvalSummary(
        total=total,
        passed=passed,
        failed=total - passed,
        pass_rate=pass_rate,
        average_quality_score=average_quality_score,
        structure_complete_rate=structure_complete_rate,
        evidence_coverage_rate=evidence_coverage_rate,
        reference_accuracy_pass_rate=reference_accuracy_pass_rate,
        fact_consistency_pass_rate=fact_consistency_pass_rate,
        results=results,
    )


def _report_metric_rate(
    results: list[LogMindReportEvalResult],
    predicate,
) -> float:
    total = len(results)
    if not total:
        return 0.0

    return sum(1 for result in results if predicate(result)) / total


def evaluate_logmind_golden_replay_case(
    case: LogMindGoldenReplayCase,
) -> LogMindGoldenReplayResult:
    input_result = evaluate_logmind_case(
        LogMindEvalCase(
            id=case.id,
            name=case.name,
            input_text=case.input_text,
            expected_fault_type=case.expected_fault_type,
            expected_diagnostic_request=True,
            required_input_evidence=case.required_input_evidence,
        )
    )
    report_result = evaluate_logmind_report_case(
        LogMindReportEvalCase(
            id=case.id,
            name=case.name,
            input_summary=case.input_text[:500],
            report_markdown=case.generated_report_markdown,
            expected_fault_type=case.expected_fault_type,
            expected_min_severity=case.expected_min_severity,
            required_evidence=case.required_report_evidence or case.required_input_evidence,
            knowledge_refs=case.knowledge_refs,
            required_grounding_terms=case.required_grounding_terms,
        )
    )
    issues = [
        f"input: {issue}" for issue in input_result.issues
    ] + [f"report: {issue}" for issue in report_result.issues]

    if report_result.quality_score < case.expected_min_quality_score:
        issues.append(
            "quality_score below threshold: "
            f"expected >= {case.expected_min_quality_score}, got {report_result.quality_score}"
        )

    return LogMindGoldenReplayResult(
        case_id=case.id,
        name=case.name,
        passed=not issues,
        input_passed=input_result.passed,
        report_passed=report_result.passed,
        quality_score=report_result.quality_score,
        expected_min_quality_score=case.expected_min_quality_score,
        issues=issues,
    )


def evaluate_logmind_golden_replay_cases(
    cases: list[LogMindGoldenReplayCase],
) -> LogMindGoldenReplaySummary:
    results = [evaluate_logmind_golden_replay_case(case) for case in cases]
    passed = sum(result.passed for result in results)
    total = len(results)
    pass_rate = passed / total if total else 0.0

    return LogMindGoldenReplaySummary(
        total=total,
        passed=passed,
        failed=total - passed,
        pass_rate=pass_rate,
        results=results,
    )


def evaluate_logmind_cases(cases: list[LogMindEvalCase]) -> LogMindEvalSummary:
    results = [evaluate_logmind_case(case) for case in cases]
    passed = sum(result.passed for result in results)
    total = len(results)
    pass_rate = passed / total if total else 0.0

    return LogMindEvalSummary(
        total=total,
        passed=passed,
        failed=total - passed,
        pass_rate=pass_rate,
        results=results,
    )


def evaluate_logmind_rag_case(
    case: LogMindRagEvalCase,
    *,
    retriever=None,
) -> LogMindRagEvalResult:
    if retriever is None:
        from core.knowledge_base import retrieve_knowledge

        retriever = retrieve_knowledge

    issues: list[str] = []
    try:
        refs = retriever(case.query, fault_type=case.fault_type, k=case.k)
    except Exception as exc:
        return LogMindRagEvalResult(
            case_id=case.id,
            name=case.name,
            passed=False,
            k=case.k,
            expected_knowledge_titles=case.expected_knowledge_titles,
            retrieved_titles=[],
            hit_titles=[],
            recall=0.0,
            issues=[f"retrieval failed: {type(exc).__name__}: {exc}"],
        )

    retrieved_titles = _dedupe_preserve_order([ref.title for ref in refs])
    hit_titles = [
        expected_title
        for expected_title in case.expected_knowledge_titles
        if _match_known_title(expected_title, retrieved_titles)
    ]
    recall = (
        len(hit_titles) / len(case.expected_knowledge_titles)
        if case.expected_knowledge_titles
        else 0.0
    )

    if len(hit_titles) < case.min_hits:
        issues.append(
            "rag hit count too low: "
            f"expected >= {case.min_hits}, got {len(hit_titles)}"
        )

    return LogMindRagEvalResult(
        case_id=case.id,
        name=case.name,
        passed=not issues,
        k=case.k,
        expected_knowledge_titles=case.expected_knowledge_titles,
        retrieved_titles=retrieved_titles,
        hit_titles=hit_titles,
        recall=recall,
        issues=issues,
    )


def evaluate_logmind_rag_cases(
    cases: list[LogMindRagEvalCase],
    *,
    retriever=None,
) -> LogMindRagEvalSummary:
    results = [
        evaluate_logmind_rag_case(case, retriever=retriever)
        for case in cases
    ]
    passed = sum(result.passed for result in results)
    total = len(results)
    pass_rate = passed / total if total else 0.0
    average_recall = (
        sum(result.recall for result in results) / total
        if total
        else 0.0
    )

    return LogMindRagEvalSummary(
        total=total,
        passed=passed,
        failed=total - passed,
        pass_rate=pass_rate,
        average_recall=average_recall,
        results=results,
    )


def _append_min_count_issue(
    issues: list[str],
    *,
    field_name: str,
    actual: int,
    expected: int,
) -> None:
    if actual < expected:
        issues.append(f"{field_name} count too low: expected >= {expected}, got {actual}")


def score_logmind_report_quality(
    *,
    case: LogMindReportEvalCase,
    missing_sections: list[str] | None = None,
    missing_evidence: list[str] | None = None,
    reference_accuracy: KnowledgeReferenceAccuracyResult | None = None,
    fact_consistency: FactConsistencyResult | None = None,
) -> dict[str, int]:
    parsed_report = parse_diagnosis_markdown(
        case.report_markdown,
        fallback_summary=case.input_summary,
        fault_type=case.expected_fault_type,
        severity=case.expected_min_severity,
    )
    if missing_sections is None:
        missing_sections = [
            section for section in REQUIRED_REPORT_SECTIONS if section not in case.report_markdown
        ]

    if missing_evidence is None:
        key_evidence_text = "\n".join(parsed_report.key_evidence).lower()
        missing_evidence = [
            evidence
            for evidence in case.required_evidence
            if evidence.lower() not in key_evidence_text
        ]

    reference_accuracy = reference_accuracy or evaluate_knowledge_reference_accuracy(
        report_markdown=case.report_markdown,
        knowledge_refs=case.knowledge_refs,
    )
    fact_consistency = fact_consistency or evaluate_fact_consistency(
        report_markdown=case.report_markdown,
        input_summary=case.input_summary,
        knowledge_refs=case.knowledge_refs,
        required_grounding_terms=case.required_grounding_terms,
    )

    return {
        "sections": _ratio_score(
            total=len(REQUIRED_REPORT_SECTIONS),
            actual=len(REQUIRED_REPORT_SECTIONS) - len(missing_sections),
            weight=REPORT_QUALITY_WEIGHTS["sections"],
        ),
        "evidence": _ratio_score(
            total=max(case.min_key_evidence, len(case.required_evidence), 1),
            actual=max(len(parsed_report.key_evidence) - len(missing_evidence), 0),
            weight=REPORT_QUALITY_WEIGHTS["evidence"],
        ),
        "causes": _ratio_score(
            total=max(case.min_possible_causes, 1),
            actual=len(parsed_report.possible_causes),
            weight=REPORT_QUALITY_WEIGHTS["causes"],
        ),
        "troubleshooting": _ratio_score(
            total=max(case.min_troubleshooting_steps, 1),
            actual=len(parsed_report.troubleshooting_steps),
            weight=REPORT_QUALITY_WEIGHTS["troubleshooting"],
        ),
        "fixes": _ratio_score(
            total=max(case.min_fix_suggestions, 1),
            actual=len(parsed_report.fix_suggestions),
            weight=REPORT_QUALITY_WEIGHTS["fixes"],
        ),
        "prevention": _ratio_score(
            total=max(case.min_prevention_suggestions, 1),
            actual=len(parsed_report.prevention_suggestions),
            weight=REPORT_QUALITY_WEIGHTS["prevention"],
        ),
        "references": _reference_score(reference_accuracy),
        "grounding": _grounding_score(
            fact_consistency=fact_consistency,
            required_grounding_terms=case.required_grounding_terms,
        ),
    }


def _ratio_score(*, total: int, actual: int, weight: int) -> int:
    if total <= 0:
        return weight

    return round(min(actual / total, 1.0) * weight)


def evaluate_knowledge_reference_accuracy(
    *,
    report_markdown: str,
    knowledge_refs: list[KnowledgeRef],
) -> KnowledgeReferenceAccuracyResult:
    cited_titles = _extract_reference_titles(report_markdown)
    known_titles = [ref.title for ref in knowledge_refs]
    issues: list[str] = []
    supported_titles: list[str] = []
    unsupported_titles: list[str] = []

    for cited_title in cited_titles:
        matched_title = _match_known_title(cited_title, known_titles)
        if matched_title:
            supported_titles.append(matched_title)
        else:
            unsupported_titles.append(cited_title)

    if unsupported_titles:
        issues.append("unsupported knowledge references: " + ", ".join(unsupported_titles))

    if known_titles and not supported_titles:
        issues.append("no retrieved knowledge reference cited in report")

    if not known_titles and cited_titles:
        issues.append("report cites knowledge references but retrieval returned no references")

    return KnowledgeReferenceAccuracyResult(
        passed=not issues,
        cited_titles=cited_titles,
        supported_titles=_dedupe_preserve_order(supported_titles),
        unsupported_titles=unsupported_titles,
        issues=issues,
    )


def evaluate_fact_consistency(
    *,
    report_markdown: str,
    input_summary: str,
    knowledge_refs: list[KnowledgeRef],
    required_grounding_terms: list[str],
) -> FactConsistencyResult:
    if not required_grounding_terms:
        return FactConsistencyResult(passed=True)

    parsed_report = parse_diagnosis_markdown(
        report_markdown,
        fallback_summary=input_summary,
    )
    source_text = _normalize_grounding_text(
        "\n".join(
            [
                input_summary,
                *[ref.title for ref in knowledge_refs],
                *[ref.snippet or "" for ref in knowledge_refs],
            ]
        )
    )
    report_claim_text = _normalize_grounding_text(
        "\n".join(
            [
                *parsed_report.possible_causes,
                *parsed_report.troubleshooting_steps,
                *parsed_report.fix_suggestions,
            ]
        )
    )
    grounded_terms: list[str] = []
    missing_from_sources: list[str] = []
    missing_from_report: list[str] = []

    for term in required_grounding_terms:
        normalized_term = _normalize_grounding_text(term)
        in_source = normalized_term in source_text
        in_report = normalized_term in report_claim_text

        if in_source and in_report:
            grounded_terms.append(term)
        if not in_source:
            missing_from_sources.append(term)
        if not in_report:
            missing_from_report.append(term)

    issues: list[str] = []
    if missing_from_sources:
        issues.append("grounding terms missing from sources: " + ", ".join(missing_from_sources))
    if missing_from_report:
        issues.append("grounding terms missing from report claims: " + ", ".join(missing_from_report))

    return FactConsistencyResult(
        passed=not issues,
        grounded_terms=grounded_terms,
        missing_from_sources=missing_from_sources,
        missing_from_report=missing_from_report,
        issues=issues,
    )


def _extract_reference_titles(report_markdown: str) -> list[str]:
    references_heading = "## 7. 参考知识"
    if references_heading not in report_markdown:
        return []

    references_text = report_markdown.split(references_heading, 1)[1].strip()
    if not references_text:
        return []

    titles: list[str] = []
    for line in references_text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        cleaned = cleaned.lstrip("-*+0123456789.、) ").strip()
        if not cleaned or any(keyword in cleaned for keyword in ("未命中", "暂无参考知识")):
            continue

        for separator in ("：", ":"):
            if separator in cleaned:
                cleaned = cleaned.split(separator, 1)[0].strip()
                break

        if cleaned:
            titles.append(cleaned)

    return _dedupe_preserve_order(titles)


def _match_known_title(cited_title: str, known_titles: list[str]) -> str | None:
    normalized_cited = _normalize_reference_title(cited_title)
    for known_title in known_titles:
        normalized_known = _normalize_reference_title(known_title)
        if normalized_cited == normalized_known:
            return known_title
        if normalized_cited in normalized_known or normalized_known in normalized_cited:
            return known_title

    return None


def _normalize_reference_title(title: str) -> str:
    return "".join(title.lower().split())


def _normalize_grounding_text(text: str) -> str:
    return "".join(text.lower().split())


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)

    return deduped


def _reference_score(reference_accuracy: KnowledgeReferenceAccuracyResult) -> int:
    if reference_accuracy.passed and reference_accuracy.cited_titles:
        return REPORT_QUALITY_WEIGHTS["references"]

    if reference_accuracy.passed and not reference_accuracy.cited_titles:
        return REPORT_QUALITY_WEIGHTS["references"]

    return 0


def _grounding_score(
    *,
    fact_consistency: FactConsistencyResult,
    required_grounding_terms: list[str],
) -> int:
    if not required_grounding_terms:
        return REPORT_QUALITY_WEIGHTS["grounding"]

    return _ratio_score(
        total=len(required_grounding_terms),
        actual=len(fact_consistency.grounded_terms),
        weight=REPORT_QUALITY_WEIGHTS["grounding"],
    )
