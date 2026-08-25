from schema import DiagnosisRecord


def build_diagnosis_markdown_export(record: DiagnosisRecord) -> str:
    sections = [
        "# LogMind 诊断报告",
        "",
        "## 基本信息",
        f"- 记录 ID：{record.id}",
        f"- 会话 ID：{record.thread_id or '未知'}",
        f"- 用户 ID：{record.user_id or '未知'}",
        f"- 故障类型：{record.fault_type.value}",
        f"- 严重等级：{record.severity.value}",
        f"- 影响组件：{record.affected_component or '未知'}",
        f"- 诊断模型：{record.model or '未知'}",
        f"- 创建时间：{record.created_at}",
        "",
        "## 问题摘要",
        record.summary or "暂无摘要",
        "",
        "## 结构化结论",
        "### 关键证据",
        _format_list(record.key_evidence),
        "",
        "### 可能原因",
        _format_list(record.possible_causes),
        "",
        "### 排查步骤",
        _format_list(record.troubleshooting_steps),
        "",
        "### 修复建议",
        _format_list(record.fix_suggestions),
        "",
        "### 后续预防建议",
        _format_list(record.prevention_suggestions),
        "",
        "## 参考知识",
        _format_knowledge_refs(record),
        "",
        "## 相似历史案例",
        _format_similar_incidents(record),
        "",
        "## Agent 执行轨迹",
        _format_agent_trace(record),
        "",
        "## 完整报告",
        record.report_markdown or "暂无完整报告",
        "",
    ]
    return "\n".join(sections)


def diagnosis_export_filename(record: DiagnosisRecord) -> str:
    safe_record_id = "".join(
        char if char.isalnum() or char in {"-", "_"} else "-" for char in record.id
    )
    return f"logmind-diagnosis-{safe_record_id}.md"


def _format_list(values: list[str]) -> str:
    if not values:
        return "- 暂无"

    return "\n".join(f"- {value}" for value in values)


def _format_knowledge_refs(record: DiagnosisRecord) -> str:
    if not record.knowledge_refs:
        return "- 暂无参考知识"

    lines: list[str] = []
    for index, ref in enumerate(record.knowledge_refs, start=1):
        lines.append(f"{index}. {ref.title}")
        lines.append(f"   - 来源：{ref.source or '本地知识库'}")
        lines.append(f"   - 摘要：{ref.snippet or '暂无摘要'}")

    return "\n".join(lines)


def _format_agent_trace(record: DiagnosisRecord) -> str:
    if not record.agent_trace:
        return "- 暂无 Agent 执行轨迹"

    lines: list[str] = []
    for index, step in enumerate(record.agent_trace, start=1):
        lines.append(f"{index}. {step.title}")
        lines.append(f"   - 步骤：{step.step}")
        lines.append(f"   - 状态：{step.status}")
        if step.detail:
            lines.append(f"   - 说明：{step.detail}")
        if step.metadata:
            metadata = ", ".join(
                f"{key}={value}" for key, value in step.metadata.items()
            )
            lines.append(f"   - 元数据：{metadata}")

    return "\n".join(lines)


def _format_similar_incidents(record: DiagnosisRecord) -> str:
    if not record.similar_incidents:
        return "- 暂无相似历史案例"

    lines: list[str] = []
    for index, incident in enumerate(record.similar_incidents, start=1):
        lines.append(f"{index}. {incident.summary}")
        lines.append(f"   - 记录 ID：{incident.record_id}")
        lines.append(f"   - 故障类型：{incident.fault_type.value}")
        lines.append(f"   - 严重等级：{incident.severity.value}")
        lines.append(f"   - 诊断时间：{incident.created_at}")
        if incident.thread_id:
            lines.append(f"   - 会话 ID：{incident.thread_id}")

    return "\n".join(lines)
