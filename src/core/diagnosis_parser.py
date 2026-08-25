import re

from schema import DiagnosisReport, FaultType, KnowledgeRef, Severity

SECTION_PATTERNS = {
    "overview": ("问题概述", "problem overview"),
    "key_evidence": ("关键信息", "关键证据", "key evidence", "key information"),
    "possible_causes": ("可能原因", "root cause", "possible cause"),
    "troubleshooting_steps": ("排查步骤", "troubleshooting"),
    "fix_suggestions": ("修复建议", "fix suggestion", "resolution"),
    "prevention_suggestions": ("预防建议", "后续预防", "prevention"),
}

SEVERITY_BY_TEXT = {
    "critical": Severity.CRITICAL,
    "严重": Severity.CRITICAL,
    "high": Severity.HIGH,
    "高": Severity.HIGH,
    "medium": Severity.MEDIUM,
    "中": Severity.MEDIUM,
    "low": Severity.LOW,
    "低": Severity.LOW,
}


def parse_diagnosis_markdown(
    report_markdown: str,
    *,
    fallback_summary: str,
    fault_type: FaultType = FaultType.UNKNOWN,
    severity: Severity = Severity.MEDIUM,
    knowledge_refs: list[KnowledgeRef] | None = None,
) -> DiagnosisReport:
    sections = _split_markdown_sections(report_markdown)
    overview_lines = _clean_section_lines(sections.get("overview", ""))

    return DiagnosisReport(
        summary=_extract_summary(overview_lines, fallback_summary),
        fault_type=fault_type,
        severity=_extract_severity(overview_lines, severity),
        affected_component=_extract_affected_component(overview_lines),
        key_evidence=_extract_list_items(sections.get("key_evidence", "")),
        possible_causes=_extract_list_items(sections.get("possible_causes", "")),
        troubleshooting_steps=_extract_list_items(sections.get("troubleshooting_steps", "")),
        fix_suggestions=_extract_list_items(sections.get("fix_suggestions", "")),
        prevention_suggestions=_extract_list_items(sections.get("prevention_suggestions", "")),
        knowledge_refs=knowledge_refs or [],
    )


def _split_markdown_sections(report_markdown: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current_key: str | None = None

    for line in report_markdown.splitlines():
        heading = _match_section_heading(line)
        if heading:
            current_key = heading
            sections.setdefault(current_key, [])
            continue

        if current_key:
            sections[current_key].append(line)

    return {key: "\n".join(lines).strip() for key, lines in sections.items()}


def _match_section_heading(line: str) -> str | None:
    normalized = line.strip().lower().lstrip("#").strip()
    normalized = re.sub(r"^\d+[.、)]\s*", "", normalized)

    for key, patterns in SECTION_PATTERNS.items():
        if any(pattern in normalized for pattern in patterns):
            return key

    return None


def _clean_section_lines(section_text: str) -> list[str]:
    return [
        line.strip()
        for line in section_text.splitlines()
        if line.strip() and not line.strip().startswith("```")
    ]


def _extract_summary(lines: list[str], fallback_summary: str) -> str:
    for line in lines:
        cleaned = _strip_list_marker(line)
        label, value = _split_label_value(cleaned)
        if label and any(keyword in label for keyword in ("简要说明", "摘要", "说明", "summary")):
            return value or fallback_summary
        if not _is_metadata_line(cleaned):
            return cleaned

    return fallback_summary


def _extract_severity(lines: list[str], fallback: Severity) -> Severity:
    for line in lines:
        cleaned = _strip_list_marker(line)
        label, value = _split_label_value(cleaned)
        if label and any(keyword in label for keyword in ("严重", "severity")):
            return _severity_from_text(value) or fallback

    return fallback


def _extract_affected_component(lines: list[str]) -> str | None:
    for line in lines:
        cleaned = _strip_list_marker(line)
        label, value = _split_label_value(cleaned)
        if label and any(keyword in label for keyword in ("影响组件", "受影响", "component")):
            return value or None

    return None


def _extract_list_items(section_text: str) -> list[str]:
    items: list[str] = []
    for line in _clean_section_lines(section_text):
        cleaned = _strip_list_marker(line)
        if cleaned:
            items.append(cleaned)

    return items


def _strip_list_marker(line: str) -> str:
    return re.sub(r"^\s*(?:[-*+]|\d+[.、)])\s*", "", line).strip()


def _split_label_value(line: str) -> tuple[str | None, str]:
    for separator in ("：", ":"):
        if separator in line:
            label, value = line.split(separator, 1)
            return label.strip().lower(), value.strip()

    return None, line


def _is_metadata_line(line: str) -> bool:
    label, _ = _split_label_value(line)
    return bool(
        label
        and any(keyword in label for keyword in ("故障类型", "严重", "影响组件", "component"))
    )


def _severity_from_text(text: str) -> Severity | None:
    normalized = text.strip().lower()
    for keyword, severity in SEVERITY_BY_TEXT.items():
        if keyword in normalized:
            return severity

    return None
