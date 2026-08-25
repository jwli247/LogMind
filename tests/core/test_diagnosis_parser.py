from core.diagnosis_parser import parse_diagnosis_markdown
from schema import FaultType, Severity


def test_parse_diagnosis_markdown_extracts_structured_sections() -> None:
    report = """
## 1. 问题概述
- 故障类型：端口冲突
- 严重等级：高
- 影响组件：Spring Boot Web Server
- 简要说明：Web 服务启动失败，8080 端口已被占用。

## 2. 关键信息提取
- Web server failed to start.
- Port 8080 was already in use.

## 3. 可能原因分析
- 旧服务实例没有退出。
- 其他进程占用了 8080 端口。

## 4. 建议排查步骤
1. 执行 netstat -ano | findstr :8080。
2. 确认占用端口的进程。

## 5. 修复建议
- 停止占用端口的进程。
- 修改 server.port。

## 6. 后续预防建议
- 为本地服务统一规划端口。
"""

    parsed = parse_diagnosis_markdown(
        report,
        fallback_summary="fallback summary",
        fault_type=FaultType.PORT_CONFLICT,
        severity=Severity.MEDIUM,
    )

    assert parsed.summary == "Web 服务启动失败，8080 端口已被占用。"
    assert parsed.fault_type == FaultType.PORT_CONFLICT
    assert parsed.severity == Severity.HIGH
    assert parsed.affected_component == "Spring Boot Web Server"
    assert parsed.key_evidence == [
        "Web server failed to start.",
        "Port 8080 was already in use.",
    ]
    assert parsed.possible_causes == [
        "旧服务实例没有退出。",
        "其他进程占用了 8080 端口。",
    ]
    assert parsed.troubleshooting_steps == [
        "执行 netstat -ano | findstr :8080。",
        "确认占用端口的进程。",
    ]
    assert parsed.fix_suggestions == [
        "停止占用端口的进程。",
        "修改 server.port。",
    ]
    assert parsed.prevention_suggestions == ["为本地服务统一规划端口。"]


def test_parse_diagnosis_markdown_uses_fallback_summary_when_sections_missing() -> None:
    parsed = parse_diagnosis_markdown(
        "plain markdown without known sections",
        fallback_summary="fallback summary",
    )

    assert parsed.summary == "fallback summary"
    assert parsed.key_evidence == []
