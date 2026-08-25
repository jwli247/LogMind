import asyncio
import json
import os
import re
import urllib.parse
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError
from streamlit.components.v1 import html

from client import AgentClient, AgentClientError
from schema import ChatHistory, ChatMessage
from schema.task_data import TaskData, TaskDataStatus
from voice import VoiceManager

# A Streamlit app for interacting with the langgraph agent via a simple chat interface.
# The app has three main functions which are all run async:

# - main() - sets up the streamlit app and high level structure
# - draw_messages() - draws a set of chat messages - either replaying existing messages
#   or streaming new ones.
# - handle_feedback() - Draws a feedback widget and records feedback from the user.

# The app heavily uses AgentClient to interact with the agent's FastAPI endpoints.


APP_TITLE = "LogMind 排障助手"
APP_ICON = "🧰"
USER_ID_COOKIE = "user_id"

FAULT_TYPE_LABELS = {
    "unknown": "未知类型",
    "port_conflict": "端口冲突",
    "connection_failure": "连接失败",
    "timeout": "请求超时",
    "gateway_5xx": "网关 5xx",
    "resource_exhaustion": "资源耗尽",
    "permission_and_auth": "权限/认证",
    "configuration_error": "配置错误",
    "container_startup_failure": "容器启动失败",
    "kubernetes_pod_failure": "K8s Pod 异常",
    "database_slow_query": "数据库慢查询",
    "disk_and_filesystem": "磁盘/文件系统",
    "tls_dns_network": "TLS/DNS/网络",
    "database_connection": "数据库连接",
    "redis_connection": "Redis 连接",
    "nginx_gateway": "Nginx 网关",
    "jvm_memory": "JVM 内存",
    "null_pointer": "空指针",
    "sql_error": "SQL 错误",
    "config_error": "配置错误",
    "permission_error": "权限错误",
    "docker_error": "Docker 错误",
}

SEVERITY_LABELS = {
    "low": "低",
    "medium": "中",
    "high": "高",
    "critical": "严重",
}

STRUCTURED_DIAGNOSIS_FIELDS = [
    ("key_evidence", "关键证据"),
    ("possible_causes", "可能原因"),
    ("troubleshooting_steps", "排查步骤"),
    ("fix_suggestions", "修复建议"),
    ("prevention_suggestions", "预防建议"),
]


def get_or_create_user_id() -> str:
    """Get the user ID from session state or URL parameters, or create a new one if it doesn't exist."""
    # Check if user_id exists in session state
    if USER_ID_COOKIE in st.session_state:
        return st.session_state[USER_ID_COOKIE]

    # Try to get from URL parameters using the new st.query_params
    if USER_ID_COOKIE in st.query_params:
        user_id = st.query_params[USER_ID_COOKIE]
        st.session_state[USER_ID_COOKIE] = user_id
        return user_id

    # Generate a new user_id if not found
    user_id = str(uuid.uuid4())

    # Store in session state for this session
    st.session_state[USER_ID_COOKIE] = user_id

    # Also add to URL parameters so it can be bookmarked/shared
    st.query_params[USER_ID_COOKIE] = user_id

    return user_id


def get_auth_headers() -> dict[str, str]:
    auth_secret = os.getenv("AUTH_SECRET")
    if not auth_secret:
        return {}

    return {"Authorization": f"Bearer {auth_secret}"}


def fetch_recent_diagnoses(
    agent_url: str,
    *,
    user_id: str,
    limit: int = 5,
) -> list[dict]:
    try:
        import httpx

        response = httpx.get(
            f"{agent_url}/diagnosis/history",
            params={"limit": limit, "user_id": user_id},
            headers=get_auth_headers(),
            timeout=5,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.warning(f"获取最近诊断记录失败：{e}")
        return []


def fetch_recent_chat_threads(
    agent_url: str,
    *,
    user_id: str,
    agent_id: str | None,
    limit: int = 10,
) -> list[dict]:
    try:
        import httpx

        response = httpx.get(
            f"{agent_url}/chat/threads",
            params={
                "limit": limit,
                "user_id": user_id,
                "agent_id": agent_id,
            },
            headers=get_auth_headers(),
            timeout=5,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.warning(f"获取最近对话失败：{e}")
        return []


def fetch_diagnosis_stats(
    agent_url: str,
    *,
    user_id: str,
    days: int = 7,
) -> dict[str, Any] | None:
    try:
        import httpx

        response = httpx.get(
            f"{agent_url}/diagnosis/stats",
            params={"days": days, "user_id": user_id},
            headers=get_auth_headers(),
            timeout=5,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.warning(f"获取诊断统计失败：{e}")
        return None


def fetch_agent_observability(
    agent_url: str,
    *,
    user_id: str,
    limit: int = 100,
) -> dict[str, Any] | None:
    try:
        import httpx

        response = httpx.get(
            f"{agent_url}/diagnosis/observability",
            params={"limit": limit, "user_id": user_id},
            headers=get_auth_headers(),
            timeout=5,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.warning(f"获取 Agent 运行观测失败：{e}")
        return None


def preview_log_file(agent_url: str, uploaded_file) -> dict[str, Any] | None:
    try:
        import httpx

        response = httpx.post(
            f"{agent_url}/diagnosis/log-file/preview",
            files={
                "file": (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    uploaded_file.type or "text/plain",
                )
            },
            headers=get_auth_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.warning(f"日志文件预处理失败：{e}")
        return None


def format_fault_type_label(fault_type: str) -> str:
    return FAULT_TYPE_LABELS.get(fault_type, fault_type)


def format_severity_label(severity: str) -> str:
    return SEVERITY_LABELS.get(severity, severity)


def format_created_at(created_at: str) -> str:
    if not created_at:
        return ""

    try:
        return datetime.fromisoformat(created_at).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return created_at


def format_source_name(source: str | None) -> str | None:
    if not source:
        return None

    return source.replace("\\", "/").rsplit("/", 1)[-1]


def render_markdown_with_code_copy(content: str) -> None:
    code_block_pattern = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)
    cursor = 0

    for match in code_block_pattern.finditer(content):
        before = content[cursor : match.start()].strip()
        if before:
            st.markdown(before)

        language = match.group(1) or None
        code = match.group(2).strip("\n")
        st.code(code, language=language)
        cursor = match.end()

    after = content[cursor:].strip()
    if after:
        st.markdown(after)


def render_copy_report_button(report_markdown: str, record_id: str | None) -> None:
    button_id = f"copy-report-{record_id or 'unknown'}".replace("-", "_")
    status_id = f"{button_id}_status"

    html(
        f"""
        <div style="display:flex;align-items:center;gap:10px;margin:4px 0 8px;">
            <button
                id="{button_id}"
                title="复制完整报告"
                style="
                    border:1px solid #d0d5dd;
                    border-radius:6px;
                    background:#ffffff;
                    color:#344054;
                    cursor:pointer;
                    font-size:16px;
                    height:32px;
                    line-height:1;
                    padding:4px 9px;
                "
            >
                ⧉
            </button>
            <span id="{status_id}" style="color:#667085;font-size:13px;"></span>
        </div>
        <script>
        const reportText = {json.dumps(report_markdown, ensure_ascii=False)};
        const button = document.getElementById({json.dumps(button_id)});
        const status = document.getElementById({json.dumps(status_id)});

        async function copyReport() {{
            try {{
                if (navigator.clipboard && window.isSecureContext) {{
                    await navigator.clipboard.writeText(reportText);
                }} else {{
                    const textArea = document.createElement("textarea");
                    textArea.value = reportText;
                    textArea.style.position = "fixed";
                    textArea.style.opacity = "0";
                    document.body.appendChild(textArea);
                    textArea.focus();
                    textArea.select();
                    document.execCommand("copy");
                    document.body.removeChild(textArea);
                }}
                status.textContent = "已复制";
            }} catch (error) {{
                status.textContent = "复制失败，请手动选择报告内容";
            }}
        }}

        button.addEventListener("click", copyReport);
        </script>
        """,
        height=48,
    )


def calculate_percentage(count: int, total: int) -> str:
    if total <= 0:
        return "0%"

    return f"{count / total:.0%}"


def build_distribution_rows(
    counts: dict[str, int],
    *,
    total: int,
    label_formatter,
) -> list[dict[str, Any]]:
    return [
        {
            "名称": label_formatter(name),
            "数量": count,
            "占比": calculate_percentage(count, total),
        }
        for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def render_distribution_section(
    title: str,
    rows: list[dict[str, Any]],
    *,
    empty_text: str,
) -> None:
    st.markdown(f"**{title}**")
    if not rows:
        st.caption(empty_text)
        return

    st.bar_chart(rows, x="名称", y="数量", use_container_width=True)
    st.dataframe(rows, hide_index=True, use_container_width=True)


def render_diagnosis_stats(stats: dict[str, Any]) -> None:
    total = stats.get("total", 0)
    by_fault_type = stats.get("by_fault_type") or {}
    by_severity = stats.get("by_severity") or {}
    daily_counts = stats.get("daily_counts") or []

    high_risk_count = by_severity.get("high", 0) + by_severity.get("critical", 0)
    top_fault_type = next(iter(by_fault_type), None)
    top_fault_count = by_fault_type.get(top_fault_type, 0) if top_fault_type else 0

    metric_total, metric_risk, metric_top = st.columns(3)
    metric_total.metric("诊断总数", total)
    metric_risk.metric("高风险诊断", high_risk_count, calculate_percentage(high_risk_count, total))
    metric_top.metric(
        "最高频故障",
        format_fault_type_label(top_fault_type) if top_fault_type else "暂无",
        f"{top_fault_count} 次" if top_fault_type else None,
    )

    if total == 0:
        st.info("当前统计范围内暂无诊断记录。")
        return

    severity_rows = build_distribution_rows(
        by_severity,
        total=total,
        label_formatter=format_severity_label,
    )
    fault_type_rows = build_distribution_rows(
        by_fault_type,
        total=total,
        label_formatter=format_fault_type_label,
    )

    st.divider()
    render_distribution_section("严重等级分布", severity_rows, empty_text="暂无严重等级数据")

    st.divider()
    render_distribution_section("故障类型排行", fault_type_rows, empty_text="暂无故障类型数据")

    if daily_counts:
        trend_rows = [
            {"日期": row.get("date"), "数量": row.get("count", 0)}
            for row in daily_counts
        ]
        st.divider()
        st.markdown("**最近趋势**")
        st.line_chart(trend_rows, x="日期", y="数量", use_container_width=True)
        st.dataframe(trend_rows, hide_index=True, use_container_width=True)


def render_agent_observability(observability: dict[str, Any]) -> None:
    total_records = observability.get("total_records", 0)
    trace_coverage_rate = observability.get("trace_coverage_rate", 0)
    average_quality_score = observability.get("average_quality_score", 0)
    failed_trace_steps = observability.get("failed_trace_steps", 0)

    metric_trace, metric_quality, metric_failed = st.columns(3)
    metric_trace.metric("轨迹覆盖率", format_rate(trace_coverage_rate))
    metric_quality.metric("平均质量分", format_score(average_quality_score))
    metric_failed.metric("失败步骤", failed_trace_steps)

    if total_records == 0:
        st.caption("暂无 Agent 运行观测数据")
        return

    metric_knowledge, metric_history, metric_reference = st.columns(3)
    metric_knowledge.metric("知识命中率", format_rate(observability.get("knowledge_hit_rate", 0)))
    metric_history.metric(
        "历史案例命中率",
        format_rate(observability.get("similar_incident_hit_rate", 0)),
    )
    metric_reference.metric(
        "引用失败记录",
        observability.get("reference_accuracy_failed_records", 0),
    )

    metric_runtime, metric_runtime_p95, metric_model_latency, metric_model_p95 = st.columns(4)
    metric_runtime.metric("平均诊断耗时", format_duration_ms(observability.get("average_runtime_ms", 0)))
    metric_runtime_p95.metric("诊断耗时 p95", format_duration_ms(observability.get("p95_runtime_ms", 0)))
    metric_model_latency.metric(
        "平均模型耗时",
        format_duration_ms(observability.get("average_model_latency_ms", 0)),
    )
    metric_model_p95.metric(
        "模型耗时 p95",
        format_duration_ms(observability.get("p95_model_latency_ms", 0)),
    )

    metric_tokens, metric_token_records, metric_cost = st.columns(3)
    metric_tokens.metric("平均 Token", format_number(observability.get("average_total_tokens", 0)))
    metric_token_records.metric("Token 记录数", observability.get("token_usage_records", 0))
    metric_cost.metric(
        "估算成本",
        format_usd(observability.get("total_estimated_cost_usd", 0)),
    )

    step_stats = observability.get("step_stats") or []
    if step_stats:
        st.markdown("**执行步骤统计**")
        st.dataframe(step_stats, hide_index=True, use_container_width=True)

    failure_reasons = observability.get("failure_reasons") or []
    if failure_reasons:
        st.markdown("**失败原因复盘**")
        render_text_list(failure_reasons)


def format_rate(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "0.0%"


def format_score(value: Any) -> str:
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return "0.0"


def format_number(value: Any) -> str:
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return "0"


def format_usd(value: Any) -> str:
    try:
        return f"${float(value):.6f}"
    except (TypeError, ValueError):
        return "$0.000000"


def format_duration_ms(value: Any) -> str:
    try:
        duration_ms = float(value)
    except (TypeError, ValueError):
        return "0 ms"

    if duration_ms >= 1000:
        return f"{duration_ms / 1000:.2f} s"

    return f"{duration_ms:.0f} ms"


def format_confidence(confidence: Any) -> str | None:
    if confidence is None:
        return None

    try:
        return f"{float(confidence):.2f}"
    except (TypeError, ValueError):
        return str(confidence)


def render_text_list(items: list[Any]) -> None:
    if not items:
        st.caption("暂无")
        return

    for item in items:
        st.markdown(f"- {item}")


def render_structured_diagnosis(record: dict[str, Any]) -> None:
    affected_component = record.get("affected_component")
    confidence_label = format_confidence(record.get("confidence"))
    has_content = bool(affected_component or confidence_label)

    if affected_component:
        st.caption(f"影响组件：{affected_component}")
    if confidence_label:
        st.caption(f"置信度：{confidence_label}")

    for field_name, label in STRUCTURED_DIAGNOSIS_FIELDS:
        values = record.get(field_name) or []
        if not values:
            continue

        has_content = True
        st.markdown(f"**{label}**")
        render_text_list(values)

    if not has_content:
        st.caption("暂无结构化结论")


def render_quality_evaluation(quality_evaluation: dict[str, Any] | None) -> None:
    if not quality_evaluation:
        st.caption("暂无质量评估")
        return

    quality_score = quality_evaluation.get("quality_score", 0)
    reference_accuracy_passed = bool(quality_evaluation.get("reference_accuracy_passed"))
    fact_consistency_passed = bool(quality_evaluation.get("fact_consistency_passed", True))

    metric_score, metric_reference, metric_fact = st.columns(3)
    metric_score.metric("质量分", f"{quality_score}/100")
    metric_reference.metric("引用准确性", "通过" if reference_accuracy_passed else "异常")
    metric_fact.metric("事实一致性", "通过" if fact_consistency_passed else "异常")

    breakdown = quality_evaluation.get("quality_breakdown") or {}
    if breakdown:
        st.markdown("**分项得分**")
        rows = [{"维度": key, "得分": value} for key, value in breakdown.items()]
        st.dataframe(rows, hide_index=True, use_container_width=True)

    cited_titles = quality_evaluation.get("cited_knowledge_titles") or []
    unsupported_titles = quality_evaluation.get("unsupported_knowledge_titles") or []
    grounded_terms = quality_evaluation.get("grounded_terms") or []
    ungrounded_terms = quality_evaluation.get("ungrounded_terms") or []
    issues = quality_evaluation.get("issues") or []

    if cited_titles:
        st.markdown("**引用知识**")
        render_text_list(cited_titles)
    if unsupported_titles:
        st.markdown("**未匹配引用**")
        render_text_list(unsupported_titles)
    if grounded_terms:
        st.markdown("**已回溯术语**")
        render_text_list(grounded_terms)
    if ungrounded_terms:
        st.markdown("**未回溯术语**")
        render_text_list(ungrounded_terms)
    if issues:
        st.markdown("**评估问题**")
        render_text_list(issues)


def render_knowledge_refs(knowledge_refs: list[dict[str, Any]]) -> None:
    if not knowledge_refs:
        st.caption("暂无参考知识")
        return

    for index, ref in enumerate(knowledge_refs, start=1):
        title = ref.get("title") or "未命名知识"
        source = ref.get("source")
        source_name = format_source_name(source)
        snippet = ref.get("snippet")

        st.markdown(f"**{index}. {title}**")
        if source_name:
            st.caption(f"来源：{source_name}")
        if snippet:
            st.write(snippet)


def render_similar_incidents(similar_incidents: list[dict[str, Any]]) -> None:
    if not similar_incidents:
        st.caption("暂无相似历史案例")
        return

    for index, incident in enumerate(similar_incidents, start=1):
        summary = incident.get("summary") or "未命名历史案例"
        fault_type = format_fault_type_label(incident.get("fault_type", "unknown"))
        severity = format_severity_label(incident.get("severity", "medium"))
        created_at = format_created_at(incident.get("created_at", ""))
        record_id = incident.get("record_id")

        st.markdown(f"**{index}. {summary}**")
        meta = [f"故障类型：{fault_type}", f"严重等级：{severity}"]
        if created_at:
            meta.append(f"诊断时间：{created_at}")
        if record_id:
            meta.append(f"记录 ID：{record_id}")
        st.caption(" | ".join(meta))


def render_agent_trace(agent_trace: list[dict[str, Any]]) -> None:
    if not agent_trace:
        st.caption("暂无 Agent 执行轨迹")
        return

    for index, step in enumerate(agent_trace, start=1):
        title = step.get("title") or step.get("step") or "未命名步骤"
        status = step.get("status") or "unknown"
        detail = step.get("detail")
        metadata = step.get("metadata") or {}

        st.markdown(f"**{index}. {title}**")
        st.caption(f"状态：{status}")
        if detail:
            st.write(detail)
        if metadata:
            st.json(metadata)


def render_recent_diagnosis_record(
    record: dict[str, Any],
    agent_url: str,
    *,
    user_id: str,
) -> None:
    record_id = record.get("id")
    thread_id = record.get("thread_id")
    fault_type = record.get("fault_type", "unknown")
    severity = record.get("severity", "medium")
    summary = record.get("summary", "")
    created_at = record.get("created_at", "")
    report_markdown = record.get("report_markdown", "")
    knowledge_refs = record.get("knowledge_refs") or []
    similar_incidents = record.get("similar_incidents") or []
    agent_trace = record.get("agent_trace") or []
    quality_evaluation = record.get("quality_evaluation")
    affected_component = record.get("affected_component")
    confidence_label = format_confidence(record.get("confidence"))
    fault_type_label = format_fault_type_label(fault_type)
    severity_label = format_severity_label(severity)
    created_at_label = format_created_at(created_at)

    st.markdown(f"**{fault_type_label} | 严重等级：{severity_label}**")
    if summary:
        st.write(summary)

    record_meta = []
    if created_at_label:
        record_meta.append(f"诊断时间：{created_at_label}")
    if affected_component:
        record_meta.append(f"影响组件：{affected_component}")
    if confidence_label:
        record_meta.append(f"置信度：{confidence_label}")
    if record_id:
        record_meta.append(f"记录 ID：{record_id}")
    if thread_id:
        record_meta.append(f"线程 ID：{thread_id}")
    if record_meta:
        st.caption(" | ".join(record_meta))

    if record_id:
        export_query = urllib.parse.urlencode({"user_id": user_id})
        export_url = (
            f"{agent_url}/diagnosis/history/"
            f"{urllib.parse.quote(str(record_id), safe='')}/export?{export_query}"
        )
        st.link_button(
            ":material/download: 下载 Markdown",
            export_url,
            use_container_width=True,
        )

    with st.expander("结构化结论", expanded=False):
        render_structured_diagnosis(record)

    with st.expander("Agent 质量评估", expanded=False):
        render_quality_evaluation(quality_evaluation)

    with st.expander("参考知识", expanded=False):
        render_knowledge_refs(knowledge_refs)

    with st.expander("相似历史案例", expanded=False):
        render_similar_incidents(similar_incidents)

    with st.expander("Agent 执行轨迹", expanded=False):
        render_agent_trace(agent_trace)

    if report_markdown:
        with st.expander("完整报告", expanded=False):
            render_copy_report_button(report_markdown, record_id)
            render_markdown_with_code_copy(report_markdown)


def get_chat_value_text(chat_value: Any) -> str:
    if isinstance(chat_value, str):
        return chat_value.strip()

    if hasattr(chat_value, "text"):
        return (chat_value.text or "").strip()

    if isinstance(chat_value, dict):
        return str(chat_value.get("text") or "").strip()

    return ""


def get_chat_value_files(chat_value: Any) -> list[Any]:
    if hasattr(chat_value, "files"):
        return list(chat_value.files or [])

    if isinstance(chat_value, dict):
        return list(chat_value.get("files") or [])

    return []


def get_chat_value_audio(chat_value: Any) -> Any | None:
    if hasattr(chat_value, "audio"):
        return chat_value.audio

    if isinstance(chat_value, dict):
        return chat_value.get("audio")

    return None


def build_logmind_chat_submission(
    *,
    chat_value: Any,
    agent_url: str | None,
    voice: VoiceManager | None,
) -> tuple[str, str] | None:
    if not chat_value:
        return None

    text = get_chat_value_text(chat_value)
    audio = get_chat_value_audio(chat_value)
    if audio and voice:
        transcribed_text = voice._transcribe_audio(audio)
        if transcribed_text:
            text = "\n\n".join(part for part in (text, transcribed_text) if part)

    files = get_chat_value_files(chat_value)
    if not files:
        return (text, text) if text else None

    if not agent_url:
        st.warning("Agent 服务地址暂不可用，无法预处理上传的日志文件。")
        return (text, text) if text else None

    diagnostic_messages = []
    uploaded_file_names = []
    for uploaded_file in files:
        preview = preview_log_file(agent_url, uploaded_file)
        if not preview:
            continue

        uploaded_file_names.append(preview.get("filename") or uploaded_file.name)
        diagnostic_messages.append(preview.get("diagnostic_message", ""))

    diagnostic_messages = [message for message in diagnostic_messages if message]
    if not diagnostic_messages:
        return (text, text) if text else None

    agent_message_parts = []
    if text:
        agent_message_parts.append(text)
    agent_message_parts.extend(diagnostic_messages)

    display_parts = []
    if text:
        display_parts.append(text)
    if uploaded_file_names:
        display_parts.append("已上传日志文件：" + "、".join(uploaded_file_names))

    return "\n\n".join(display_parts), "\n\n---\n\n".join(agent_message_parts)


async def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        menu_items={},
    )

    # Hide the streamlit upper-right chrome
    st.html(
        """
        <style>
        :root {
            --logmind-ink: #182230;
            --logmind-muted: #667085;
            --logmind-border: #dde3ea;
            --logmind-panel: #f6f8fa;
            --logmind-nav-active: #e7e9ed;
        }
        [data-testid="stStatusWidget"] {
            visibility: hidden;
            height: 0%;
            position: fixed;
        }
        [data-testid="stAppViewContainer"] {
            background: #fcfcfd;
            color: var(--logmind-ink);
        }
        [data-testid="stHeader"] {
            background: rgba(252, 252, 253, 0.88);
        }
        [data-testid="stMainBlockContainer"] {
            max-width: 1040px;
            padding: 2rem 2.5rem 7.25rem;
        }
        [data-testid="stSidebar"] {
            background: var(--logmind-panel);
            border-right: 1px solid var(--logmind-border);
        }
        [data-testid="stSidebar"] > div:first-child {
            padding: 1.8rem 1.25rem 1.25rem;
        }
        [data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"] {
            display: flex;
            flex-direction: column;
            gap: 0.55rem;
            min-height: calc(100vh - 7.5rem);
        }
        [data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-bottom-spacer) {
            flex: 1 1 auto;
        }
        [data-testid="stSidebar"] h2 {
            color: var(--logmind-ink);
            font-size: 1.15rem;
            margin-bottom: 0.3rem;
        }
        [data-testid="stSidebar"] .sidebar-brand {
            padding: 0.1rem 0 0.35rem;
        }
        [data-testid="stSidebar"] .sidebar-brand-title {
            align-items: center;
            color: var(--logmind-ink);
            display: flex;
            font-size: 1.15rem;
            font-weight: 650;
            gap: 0.4rem;
            justify-content: center;
            line-height: 1.35;
        }
        [data-testid="stSidebar"] .sidebar-brand-icon {
            display: inline-flex;
            flex: 0 0 1.25rem;
            justify-content: center;
            min-width: 0;
            width: 1.25rem;
        }
        [data-testid="stSidebar"] .sidebar-brand-subtitle {
            color: var(--logmind-muted);
            font-size: 0.88rem;
            line-height: 1.55;
            margin-top: 0.3rem;
            text-align: center;
        }
        [data-testid="stSidebar"] p {
            color: var(--logmind-muted);
            font-size: 0.88rem;
            line-height: 1.55;
        }
        [data-testid="stSidebar"] .stButton > button {
            background: transparent;
            border: 0;
            border-radius: 6px;
            color: #344054;
            justify-content: flex-start;
            min-height: 2.45rem;
            padding: 0.45rem 0.65rem;
        }
        [data-testid="stSidebar"] .stButton > button:hover,
        [data-testid="stSidebar"] .stButton > button:focus-visible,
        [data-testid="stSidebar"] .stButton > button:focus {
            background: var(--logmind-nav-active);
            color: #344054;
        }
        [data-testid="stSidebar"] .stButton > button[kind="primary"] {
            background: transparent;
            color: #344054;
            justify-content: flex-start;
        }
        [data-testid="stSidebar"] [data-testid="stPopoverButton"] {
            background: transparent;
            border: 0;
            border-radius: 6px;
            box-shadow: none;
            color: #344054;
            justify-content: flex-start;
            min-height: 2.45rem;
            padding: 0.45rem 0.65rem;
            width: 100%;
        }
        [data-testid="stSidebar"] [data-testid="stPopoverButton"] > div {
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            align-items: center;
            width: 100%;
        }
        [data-testid="stSidebar"] [data-testid="stPopoverButton"] > div > div:first-child {
            grid-column: 2;
        }
        [data-testid="stSidebar"] [data-testid="stPopoverButton"] [aria-hidden="true"] {
            grid-column: 3;
            justify-self: start;
            margin-left: 0.25rem;
        }
        [data-testid="stSidebar"] [data-testid="stPopoverButton"]:hover,
        [data-testid="stSidebar"] [data-testid="stPopoverButton"]:focus-visible,
        [data-testid="stSidebar"] [data-testid="stPopoverButton"][aria-expanded="true"] {
            background: var(--logmind-nav-active);
            color: #344054;
        }
        [data-testid="stChatInput"] {
            background: #ffffff;
            border: 1px solid var(--logmind-border);
            border-radius: 8px;
            box-shadow: 0 8px 22px rgba(16, 24, 40, 0.08);
        }
        [data-testid="stChatInput"]:focus-within {
            border-color: var(--logmind-accent);
            box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.12);
        }
        [data-testid="stChatInput"] textarea {
            color: var(--logmind-ink);
            font-size: 0.95rem;
        }
        [data-testid="stChatMessage"] {
            gap: 0.7rem;
            padding: 0.15rem 0;
        }
        [data-testid="stChatMessage"] p,
        [data-testid="stChatMessage"] li {
            color: #344054;
        }
        [data-testid="stChatMessage"] h1 {
            color: var(--logmind-ink);
            font-size: 1.35rem;
            line-height: 1.35;
            margin: 0.65rem 0 0.4rem;
        }
        [data-testid="stChatMessage"] h2 {
            color: var(--logmind-ink);
            font-size: 1.14rem;
            line-height: 1.35;
            margin: 0.6rem 0 0.35rem;
        }
        [data-testid="stChatMessage"] h3 {
            color: var(--logmind-ink);
            font-size: 1rem;
            line-height: 1.35;
            margin: 0.55rem 0 0.35rem;
        }
        [data-testid="stChatMessage"] p,
        [data-testid="stChatMessage"] li {
            line-height: 1.7;
        }
        [data-testid="stChatMessage"] pre {
            border: 1px solid var(--logmind-border);
            border-radius: 6px;
            font-size: 0.88rem;
        }
        [data-testid="stExpander"] {
            border: 1px solid var(--logmind-border);
            border-radius: 6px;
            margin-bottom: 0.55rem;
        }
        [data-testid="stExpander"] summary {
            color: #344054;
            font-size: 0.92rem;
        }
        [data-testid="stExpander"] h1 {
            font-size: 1.22rem;
        }
        [data-testid="stExpander"] h2 {
            font-size: 1.08rem;
        }
        [data-testid="stExpander"] h3 {
            font-size: 0.98rem;
        }
        [data-testid="stMetric"] {
            border-top: 1px solid var(--logmind-border);
            padding-top: 0.7rem;
        }
        div[role="dialog"] {
            border-radius: 8px;
        }
        @media (max-width: 700px) {
            [data-testid="stMainBlockContainer"] {
                padding: 1.25rem 1rem 6.5rem;
            }
            [data-testid="stChatMessage"] {
                gap: 0.55rem;
            }
            [data-testid="stChatMessage"] h1 {
                font-size: 1.22rem;
            }
            [data-testid="stChatMessage"] h2 {
                font-size: 1.06rem;
            }
            [data-testid="stChatInput"] textarea {
                font-size: 0.9rem;
            }
        }
        </style>
        """,
    )
    if st.get_option("client.toolbarMode") != "minimal":
        st.set_option("client.toolbarMode", "minimal")
        await asyncio.sleep(0.1)
        st.rerun()

    # Get or create user ID
    user_id = get_or_create_user_id()

    if "agent_client" not in st.session_state:
        load_dotenv()
        agent_url = os.getenv("AGENT_URL")
        if not agent_url:
            host = os.getenv("HOST", "0.0.0.0")
            port = os.getenv("PORT", 8080)
            agent_url = f"http://{host}:{port}"
        try:
            with st.spinner("正在连接 Agent 服务..."):
                st.session_state.agent_client = AgentClient(base_url=agent_url)
                st.session_state.agent_url = agent_url
        except AgentClientError as e:
            st.error(f"连接 Agent 服务失败，服务地址：{agent_url}，错误信息：{e}")
            st.markdown("服务可能仍在启动中，请等待几秒后重试。")
            st.stop()
    agent_client: AgentClient = st.session_state.agent_client

    # Initialize voice manager (once per session)
    if "voice_manager" not in st.session_state:
        st.session_state.voice_manager = VoiceManager.from_env()
    voice = st.session_state.voice_manager

    if "thread_id" not in st.session_state:
        thread_id = st.query_params.get("thread_id")
        if not thread_id:
            thread_id = str(uuid.uuid4())
            messages = []
        else:
            # Read the agent from the URL so history is fetched through the graph that
            # created the thread.
            resume_agent = st.query_params.get("agent") or agent_client.agent
            try:
                messages: ChatHistory = agent_client.get_history(
                    thread_id=thread_id, agent=resume_agent
                ).messages
            except AgentClientError:
                st.error("当前会话没有找到历史记录，可能是链接中的 thread_id 已失效。请点击“新建对话”重新开始。")
                if st.button(":material/add: 新建对话", type="primary", key="recover-stale-chat"):
                    del st.query_params["thread_id"]
                    st.query_params.pop("agent", None)
                    st.rerun()
                messages = []
        st.session_state.messages = messages
        st.session_state.thread_id = thread_id

    # Keep thread_id in the URL so the address bar is directly shareable.
    st.query_params["thread_id"] = st.session_state.thread_id

    # Config options
    with st.sidebar:
        st.markdown(
            f"""
            <div class="sidebar-brand">
                <div class="sidebar-brand-title">
                    <span class="sidebar-brand-icon">{APP_ICON}</span>
                    <span>{APP_TITLE}</span>
                </div>
                <div class="sidebar-brand-subtitle">日志分析与运维排障工作台</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(":material/chat: 新建对话", type="primary", use_container_width=True):
            st.session_state.messages = []
            st.session_state.thread_id = str(uuid.uuid4())
            # Clear saved audio when starting new chat
            if "last_audio" in st.session_state:
                del st.session_state.last_audio
            st.rerun()

        @st.dialog("最近对话")
        def recent_chats_dialog() -> None:
            agent_url = st.session_state.get("agent_url")
            if not agent_url:
                st.info("Agent 服务地址暂不可用，请刷新页面后重试。")
                return

            threads = fetch_recent_chat_threads(
                agent_url,
                user_id=user_id,
                agent_id=agent_client.agent,
                limit=10,
            )
            if not threads:
                st.info("暂无最近对话。发送一条消息后，这里会出现会话入口。")
                return

            for thread in threads:
                thread_id = thread.get("thread_id")
                agent_id = thread.get("agent_id") or agent_client.agent
                title = thread.get("title") or "未命名对话"
                summary = thread.get("last_message_summary") or ""
                updated_at = format_created_at(thread.get("updated_at", ""))

                st.markdown(f"**{title}**")
                if summary and summary != title:
                    st.write(summary)
                if updated_at:
                    st.caption(f"最后更新：{updated_at}")
                if thread_id:
                    st.caption(f"线程 ID：{thread_id}")
                    if st.button(
                        ":material/open_in_new: 打开",
                        key=f"open-chat-{agent_id}-{thread_id}",
                        use_container_width=True,
                    ):
                        try:
                            history = agent_client.get_history(
                                thread_id=thread_id,
                                agent=agent_id,
                            )
                        except AgentClientError as e:
                            st.error(f"恢复对话失败：{e}")
                            return

                        st.session_state.messages = history.messages
                        st.session_state.thread_id = thread_id
                        st.query_params["thread_id"] = thread_id
                        if agent_id:
                            agent_client.agent = agent_id
                            st.query_params["agent"] = agent_id
                        st.session_state.pop("last_audio", None)
                        st.rerun()
                st.divider()

        if st.button(":material/forum: 最近对话", use_container_width=True):
            recent_chats_dialog()

        @st.dialog("系统架构")
        def architecture_dialog() -> None:
            st.code(
                "日志输入 / 文件上传\n"
                "        ↓\n"
                "脱敏 → 意图识别 → 故障分类\n"
                "        ↓\n"
                "知识库检索 + 历史案例召回\n"
                "        ↓\n"
                "LLM 诊断报告 → 质量评估 → 历史沉淀",
                language=None,
            )
            st.caption("诊断过程会记录 Agent Trace、引用信息和质量结果，便于后续复盘。")

        if st.button(":material/schema: 系统架构", use_container_width=True):
            architecture_dialog()

        @st.dialog("分享/恢复对话")
        def share_chat_dialog() -> None:
            # st.context.url is the browser URL (with query string stripped). Rebuild
            # the params, including the agent so the thread resumes through the right graph.
            if not st.context.url:
                st.error("无法获取当前应用地址，暂时不能生成分享链接。")
                return
            query = urllib.parse.urlencode(
                {
                    "thread_id": st.session_state.thread_id,
                    "agent": agent_client.agent,
                    USER_ID_COOKIE: user_id,
                }
            )
            chat_url = f"{st.context.url}?{query}"
            st.markdown(f"**当前对话链接：**\n```text\n{chat_url}\n```")
            st.info("复制上面的链接，可以分享或恢复当前对话。")

        if st.button(":material/link: 分享/恢复对话", use_container_width=True):
            share_chat_dialog()

        @st.dialog("诊断统计")
        def diagnosis_stats_dialog() -> None:
            agent_url = st.session_state.get("agent_url")
            if not agent_url:
                st.info("Agent 服务地址暂不可用，请刷新页面后重试。")
                return

            days = st.slider("统计范围（天）", min_value=1, max_value=30, value=7)
            stats = fetch_diagnosis_stats(agent_url, user_id=user_id, days=days)
            if stats:
                render_diagnosis_stats(stats)
            observability = fetch_agent_observability(agent_url, user_id=user_id)
            if observability:
                st.divider()
                st.markdown("**Agent 运行观测**")
                render_agent_observability(observability)

        if st.button(":material/monitoring: 诊断统计", use_container_width=True):
            diagnosis_stats_dialog()

        @st.dialog("最近诊断")
        def recent_diagnoses_dialog() -> None:
            agent_url = st.session_state.get("agent_url")
            if not agent_url:
                st.info("Agent 服务地址暂不可用，请刷新页面后重试。")
                return

            records = fetch_recent_diagnoses(agent_url, user_id=user_id, limit=5)
            if not records:
                st.info("暂无诊断记录。")
                return

            for record in records:
                render_recent_diagnosis_record(record, agent_url, user_id=user_id)
                st.divider()


        if st.button(":material/history: 最近诊断", use_container_width=True):
            recent_diagnoses_dialog()

        st.markdown('<div class="sidebar-bottom-spacer"></div>', unsafe_allow_html=True)
        st.divider()

        with st.popover(":material/settings: 设置", use_container_width=True):
            model_idx = agent_client.info.models.index(agent_client.info.default_model)
            model = st.selectbox("选择模型", options=agent_client.info.models, index=model_idx)
            agent_list = [a.key for a in agent_client.info.agents]
            agent_idx = agent_list.index(agent_client.info.default_agent)
            # Sync the selection to the ?agent= URL param (dropped when it's the default).
            agent_client.agent = st.selectbox(
                "选择 Agent",
                options=agent_list,
                index=agent_idx,
                key="agent",
                bind="query-params",
            )
            use_streaming = st.toggle("流式输出", value=True)
            # Audio toggle with callback: clears cached audio when toggled off
            enable_audio = st.toggle(
                "启用语音生成",
                value=True,
                disabled=not voice or not voice.tts,
                help="在 .env 中配置 VOICE_TTS_PROVIDER 后可启用"
                if not voice or not voice.tts
                else None,
                on_change=lambda: (
                    st.session_state.pop("last_audio", None)
                    if not st.session_state.get("enable_audio", True)
                    else None
                ),
                key="enable_audio",
            )

            # Display user ID (for debugging or user information)
            st.text_input("用户 ID（只读）", value=user_id, disabled=True)

        with st.popover(":material/policy: 隐私说明", use_container_width=True):
            st.write(
                "本地开发环境下，请不要输入真实敏感信息、账号密码、生产环境日志或内部数据。后续正式部署时，需要增加鉴权、日志脱敏和访问控制。"
            )

    # Draw existing messages
    messages: list[ChatMessage] = st.session_state.messages

    if len(messages) == 0:
        match agent_client.agent:
            case "logmind":
                WELCOME = """你好，我是 LogMind 智能日志分析与运维排障 Agent。
你可以粘贴 Spring Boot、MySQL、Redis、Nginx、Docker 等相关日志或异常堆栈，我会帮你提取关键信息、分析可能原因，并给出排查步骤和修复建议。"""
            case "chatbot":
                WELCOME = "你好，我是 LogMind 智能排障助手。你可以粘贴日志或描述系统故障，我会帮你分析可能原因。"
            case "research-assistant":
                WELCOME = """你好，我是 LogMind 智能运维排障助手。
        你可以输入 Java、Python、MySQL、Redis、Nginx、Docker 等相关报错信息，我会帮你分析故障原因并给出处理建议。"""
            case "rag-assistant":
                WELCOME = """你好，我是 LogMind 知识库辅助诊断助手。
        我可以结合运维知识库、历史故障案例和你提供的日志信息，帮助你分析故障原因、定位问题并生成排查建议。"""
            case _:
                WELCOME = "你好，我是智能 Agent 助手。请描述你的问题，我会尽力帮助你分析。"

        with st.chat_message("ai"):
            st.write(WELCOME)

    # draw_messages() expects an async iterator over messages
    async def amessage_iter() -> AsyncGenerator[ChatMessage, None]:
        for m in messages:
            yield m

    await draw_messages(amessage_iter())

    # Render saved audio for the last AI message (if it exists)
    # This ensures audio persists across st.rerun() calls
    if (
        voice
        and enable_audio
        and "last_audio" in st.session_state
        and st.session_state.last_message
        and len(messages) > 0
        and messages[-1].type == "ai"
    ):
        with st.session_state.last_message:
            audio_data = st.session_state.last_audio
            st.audio(audio_data["data"], format=audio_data["format"])

    # Generate new message if the user provided new input
    # Use voice manager if available, otherwise fall back to regular input
    # REQUIRED: Set VOICE_STT_PROVIDER, VOICE_TTS_PROVIDER, OPENAI_API_KEY
    # in app .env (NOT service .env) to enable voice features.
    if agent_client.agent == "logmind":
        chat_value = st.chat_input(
            "请粘贴日志、报错堆栈，或描述你遇到的系统故障...",
            accept_file="multiple",
            file_type=["log", "txt"],
            accept_audio=bool(voice and voice.stt),
        )
        submission = build_logmind_chat_submission(
            chat_value=chat_value,
            agent_url=st.session_state.get("agent_url"),
            voice=voice,
        )
    elif voice:
        user_input = voice.get_chat_input()
        submission = (user_input, user_input) if user_input else None
    else:
        user_input = st.chat_input("请粘贴日志、报错堆栈，或描述你遇到的系统故障...")
        submission = (user_input, user_input) if user_input else None

    if submission:
        display_input, agent_input = submission
        messages.append(ChatMessage(type="human", content=display_input))
        st.chat_message("human").write(display_input)
        try:
            thinking_status = st.status("正在思考...", state="running", expanded=False)

            if use_streaming:
                with thinking_status:
                    stream = agent_client.astream(
                        message=agent_input,
                        model=model,
                        thread_id=st.session_state.thread_id,
                        user_id=user_id,
                    )
                    await draw_messages(stream, is_new=True)
                    thinking_status.update(label="已完成", state="complete")
                    # Generate TTS audio for streaming response
                    # Note: draw_messages() stores the final message in st.session_state.messages
                    # and the container reference in st.session_state.last_message
                    if voice and enable_audio and st.session_state.messages:
                        last_msg = st.session_state.messages[-1]
                        # Only generate audio for AI responses with content
                        if last_msg.type == "ai" and last_msg.content:
                            # Use audio_only=True since text was already streamed by draw_messages()
                            voice.render_message(
                                last_msg.content,
                                container=st.session_state.last_message,
                                audio_only=True,
                            )
            else:
                with thinking_status:
                    response = await agent_client.ainvoke(
                        message=agent_input,
                        model=model,
                        thread_id=st.session_state.thread_id,
                        user_id=user_id,
                    )
                    thinking_status.update(label="已完成", state="complete")
                messages.append(response)
                # Render AI response with optional voice
                with st.chat_message("ai"):
                    if voice and enable_audio:
                        voice.render_message(response.content)
                    else:
                        render_markdown_with_code_copy(response.content)
            st.rerun()  # Clear stale containers
        except AgentClientError as e:
            st.error(f"生成回复失败：{e}")
            st.stop()

    # If messages have been generated, show feedback widget
    if len(messages) > 0 and st.session_state.last_message:
        with st.session_state.last_message:
            await handle_feedback()


async def draw_messages(
    messages_agen: AsyncGenerator[ChatMessage | str, None],
    is_new: bool = False,
) -> None:
    """
    Draws a set of chat messages - either replaying existing messages
    or streaming new ones.

    This function has additional logic to handle streaming tokens and tool calls.
    - Use a placeholder container to render streaming tokens as they arrive.
    - Use a status container to render tool calls. Track the tool inputs and outputs
      and update the status container accordingly.

    The function also needs to track the last message container in session state
    since later messages can draw to the same container. This is also used for
    drawing the feedback widget in the latest chat message.

    Args:
        messages_aiter: An async iterator over messages to draw.
        is_new: Whether the messages are new or not.
    """

    # Keep track of the last message container
    last_message_type = None
    st.session_state.last_message = None

    # Placeholder for intermediate streaming tokens
    streaming_content = ""
    streaming_placeholder = None

    # Iterate over the messages and draw them
    while msg := await anext(messages_agen, None):
        # str message represents an intermediate token being streamed
        if isinstance(msg, str):
            # If placeholder is empty, this is the first token of a new message
            # being streamed. We need to do setup.
            if not streaming_placeholder:
                if last_message_type != "ai":
                    last_message_type = "ai"
                    st.session_state.last_message = st.chat_message("ai")
                with st.session_state.last_message:
                    streaming_placeholder = st.empty()

            streaming_content += msg
            streaming_placeholder.write(streaming_content)
            continue
        if not isinstance(msg, ChatMessage):
            st.error(f"Unexpected message type: {type(msg)}")
            st.write(msg)
            st.stop()

        match msg.type:
            # A message from the user, the easiest case
            case "human":
                last_message_type = "human"
                st.chat_message("human").write(msg.content)

            # A message from the agent is the most complex case, since we need to
            # handle streaming tokens and tool calls.
            case "ai":
                # If we're rendering new messages, store the message in session state
                if is_new:
                    st.session_state.messages.append(msg)

                # If the last message type was not AI, create a new chat message
                if last_message_type != "ai":
                    last_message_type = "ai"
                    st.session_state.last_message = st.chat_message("ai")

                with st.session_state.last_message:
                    # If the message has content, write it out.
                    # Reset the streaming variables to prepare for the next message.
                    if msg.content:
                        if streaming_placeholder:
                            streaming_placeholder.write(msg.content)
                            streaming_content = ""
                            streaming_placeholder = None
                        else:
                            render_markdown_with_code_copy(msg.content)

                    if msg.tool_calls:
                        # Create a status container for each tool call and store the
                        # status container by ID to ensure results are mapped to the
                        # correct status container.
                        call_results = {}
                        for tool_call in msg.tool_calls:
                            # Use different labels for transfer vs regular tool calls
                            if "transfer_to" in tool_call["name"]:
                                label = f"""💼 子 Agent：{tool_call["name"]}"""
                            else:
                                label = f"""🛠️ 工具调用：{tool_call["name"]}"""

                            status = st.status(
                                label,
                                state="running" if is_new else "complete",
                            )
                            call_results[tool_call["id"]] = status

                        # Expect one ToolMessage for each tool call.
                        for tool_call in msg.tool_calls:
                            if "transfer_to" in tool_call["name"]:
                                status = call_results[tool_call["id"]]
                                status.update(expanded=True)
                                await handle_sub_agent_msgs(messages_agen, status, is_new)
                                break

                            # Only non-transfer tool calls reach this point
                            status = call_results[tool_call["id"]]
                            status.write("输入：")
                            status.write(tool_call["args"])
                            tool_result: ChatMessage = await anext(messages_agen)

                            if tool_result.type != "tool":
                                st.error(f"Unexpected ChatMessage type: {tool_result.type}")
                                st.write(tool_result)
                                st.stop()

                            # Record the message if it's new, and update the correct
                            # status container with the result
                            if is_new:
                                st.session_state.messages.append(tool_result)
                            if tool_result.tool_call_id:
                                status = call_results[tool_result.tool_call_id]
                            status.write("输出：")
                            status.write(tool_result.content)
                            status.update(state="complete")

            case "custom":
                # CustomData example used by the bg-task-agent
                # See:
                # - src/agents/utils.py CustomData
                # - src/agents/bg_task_agent/task.py
                try:
                    task_data: TaskData = TaskData.model_validate(msg.custom_data)
                except ValidationError:
                    st.error("收到 Agent 返回的异常自定义消息。")
                    st.write(msg.custom_data)
                    st.stop()

                if is_new:
                    st.session_state.messages.append(msg)

                if last_message_type != "task":
                    last_message_type = "task"
                    st.session_state.last_message = st.chat_message(
                        name="task", avatar=":material/manufacturing:"
                    )
                    with st.session_state.last_message:
                        status = TaskDataStatus()

                status.add_and_draw_task_data(task_data)

            # In case of an unexpected message type, log an error and stop
            case _:
                st.error(f"Unexpected ChatMessage type: {msg.type}")
                st.write(msg)
                st.stop()


async def handle_feedback() -> None:
    """Draws a feedback widget and records feedback from the user."""

    # Keep track of last feedback sent to avoid sending duplicates
    if "last_feedback" not in st.session_state:
        st.session_state.last_feedback = (None, None)

    latest_run_id = st.session_state.messages[-1].run_id
    feedback = st.feedback("stars", key=latest_run_id)

    # If the feedback value or run ID has changed, send a new feedback record
    if feedback is not None and (latest_run_id, feedback) != st.session_state.last_feedback:
        # Normalize the feedback value (an index) to a score between 0 and 1
        normalized_score = (feedback + 1) / 5.0

        agent_client: AgentClient = st.session_state.agent_client
        try:
            await agent_client.acreate_feedback(
                run_id=latest_run_id,
                key="human-feedback-stars",
                score=normalized_score,
                kwargs={"comment": "In-line human feedback"},
            )
        except AgentClientError as e:
            st.error(f"记录反馈失败：{e}")
            st.stop()
        st.session_state.last_feedback = (latest_run_id, feedback)
        st.toast("反馈已记录", icon=":material/reviews:")


async def handle_sub_agent_msgs(messages_agen, status, is_new):
    """
    This function segregates agent output into a status container.
    It handles all messages after the initial tool call message
    until it reaches the final AI message.

    Enhanced to support nested multi-agent hierarchies with handoff back messages.

    Args:
        messages_agen: Async generator of messages
        status: the status container for the current agent
        is_new: Whether messages are new or replayed
    """
    nested_popovers = {}

    # looking for the transfer Success tool call message
    first_msg = await anext(messages_agen)
    if is_new:
        st.session_state.messages.append(first_msg)

    # Continue reading until we get an explicit handoff back
    while True:
        # Read next message
        sub_msg = await anext(messages_agen)

        # this should only happen is skip_stream flag is removed
        # if isinstance(sub_msg, str):
        #     continue

        if is_new:
            st.session_state.messages.append(sub_msg)

        # Handle tool results with nested popovers
        if sub_msg.type == "tool" and sub_msg.tool_call_id in nested_popovers:
            popover = nested_popovers[sub_msg.tool_call_id]
            popover.write("**输出：**")
            popover.write(sub_msg.content)
            continue

        # Handle transfer_back_to tool calls - these indicate a sub-agent is returning control
        if (
            hasattr(sub_msg, "tool_calls")
            and sub_msg.tool_calls
            and any("transfer_back_to" in tc.get("name", "") for tc in sub_msg.tool_calls)
        ):
            # Process transfer_back_to tool calls
            for tc in sub_msg.tool_calls:
                if "transfer_back_to" in tc.get("name", ""):
                    # Read the corresponding tool result
                    transfer_result = await anext(messages_agen)
                    if is_new:
                        st.session_state.messages.append(transfer_result)

            # After processing transfer back, we're done with this agent
            if status:
                status.update(state="complete")
            break

        # Display content and tool calls in the same nested status
        if status:
            if sub_msg.content:
                status.write(sub_msg.content)

            if hasattr(sub_msg, "tool_calls") and sub_msg.tool_calls:
                for tc in sub_msg.tool_calls:
                    # Check if this is a nested transfer/delegate
                    if "transfer_to" in tc["name"]:
                        # Create a nested status container for the sub-agent
                        nested_status = status.status(
                            f"""💼 子 Agent：{tc["name"]}""",
                            state="running" if is_new else "complete",
                            expanded=True,
                        )

                        # Recursively handle sub-agents of this sub-agent
                        await handle_sub_agent_msgs(messages_agen, nested_status, is_new)
                    else:
                        # Regular tool call - create popover
                        popover = status.popover(f"{tc['name']}", icon="🛠️")
                        popover.write(f"**工具：** {tc['name']}")
                        popover.write("**输入：**")
                        popover.write(tc["args"])
                        # Store the popover reference using the tool call ID
                        nested_popovers[tc["id"]] = popover


if __name__ == "__main__":
    asyncio.run(main())
