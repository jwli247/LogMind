from pathlib import Path

from core.logmind_eval import (
    LogMindEvalCase,
    LogMindGoldenReplayCase,
    LogMindRagEvalCase,
    LogMindReportEvalCase,
    evaluate_fact_consistency,
    evaluate_knowledge_reference_accuracy,
    evaluate_logmind_case,
    evaluate_logmind_cases,
    evaluate_logmind_golden_replay_case,
    evaluate_logmind_golden_replay_cases,
    evaluate_logmind_rag_case,
    evaluate_logmind_rag_cases,
    evaluate_logmind_report_case,
    evaluate_logmind_report_cases,
    load_logmind_eval_cases,
    load_logmind_golden_replay_cases,
    load_logmind_rag_eval_cases,
    load_logmind_report_eval_cases,
    score_logmind_report_quality,
)
from schema import FaultType, KnowledgeRef, Severity

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "logmind_eval_cases.json"
REPORT_FIXTURE_PATH = (
    Path(__file__).parents[1] / "fixtures" / "logmind_report_eval_cases.json"
)
GOLDEN_FIXTURE_PATH = (
    Path(__file__).parents[1] / "fixtures" / "logmind_golden_replay_cases.json"
)
RAG_FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "logmind_rag_eval_cases.json"
PUBLIC_LOG_FIXTURE_PATH = (
    Path(__file__).parents[1] / "fixtures" / "logmind_public_log_eval_cases.json"
)
EXTERNAL_FIXTURE_PATH = (
    Path(__file__).parents[1] / "fixtures" / "logmind_external_annotated_cases.json"
)


def test_load_logmind_eval_cases_from_fixture() -> None:
    cases = load_logmind_eval_cases(FIXTURE_PATH)

    assert len(cases) >= 40
    assert cases[0].id == "port_conflict_spring_boot_8080"
    assert cases[0].expected_fault_type == FaultType.PORT_CONFLICT


def test_evaluate_logmind_cases_fixture_passes() -> None:
    cases = load_logmind_eval_cases(FIXTURE_PATH)
    summary = evaluate_logmind_cases(cases)

    assert summary.failed == 0
    assert summary.passed == summary.total
    assert summary.pass_rate == 1.0


def test_evaluate_public_log_eval_cases_fixture_passes() -> None:
    cases = load_logmind_eval_cases(PUBLIC_LOG_FIXTURE_PATH)
    summary = evaluate_logmind_cases(cases)

    assert len(cases) >= 10
    assert all(case.dataset for case in cases)
    assert all(case.source_url for case in cases)
    assert summary.failed == 0
    assert summary.pass_rate == 1.0


def test_evaluate_external_annotated_cases_fixture_passes() -> None:
    cases = load_logmind_eval_cases(EXTERNAL_FIXTURE_PATH)
    summary = evaluate_logmind_cases(cases)

    assert len(cases) >= 40
    assert all(case.dataset == "External annotated cases" for case in cases)
    assert all(case.source_url for case in cases)
    assert summary.failed == 0
    assert summary.pass_rate == 1.0


def test_evaluate_logmind_case_reports_fault_type_mismatch() -> None:
    case = LogMindEvalCase(
        id="mismatch",
        name="分类不匹配",
        input_text="Web server failed to start. Port 8080 was already in use.",
        expected_fault_type=FaultType.CONNECTION_FAILURE,
        expected_diagnostic_request=True,
    )

    result = evaluate_logmind_case(case)

    assert not result.passed
    assert result.predicted_fault_type == FaultType.PORT_CONFLICT
    assert "fault_type mismatch" in result.issues[0]


def test_load_logmind_rag_eval_cases_from_fixture() -> None:
    cases = load_logmind_rag_eval_cases(RAG_FIXTURE_PATH)

    assert len(cases) >= 24
    assert cases[0].id == "rag_port_conflict_1"
    assert cases[0].expected_knowledge_titles == ["端口冲突排查手册"]
    assert cases[0].k == 3


def test_evaluate_logmind_rag_case_accepts_expected_top_k_hit() -> None:
    case = LogMindRagEvalCase(
        id="rag_hit",
        name="RAG 命中",
        query="Port 8080 was already in use.",
        fault_type=FaultType.PORT_CONFLICT,
        expected_knowledge_titles=["端口冲突排查手册"],
        k=3,
    )

    result = evaluate_logmind_rag_case(
        case,
        retriever=lambda *_args, **_kwargs: [
            KnowledgeRef(
                title="端口冲突排查手册",
                source="docs/knowledge/port_conflict.md",
                snippet="Port already in use.",
            )
        ],
    )

    assert result.passed
    assert result.hit_titles == ["端口冲突排查手册"]
    assert result.recall == 1.0


def test_evaluate_logmind_rag_case_reports_missing_top_k_hit() -> None:
    case = LogMindRagEvalCase(
        id="rag_miss",
        name="RAG 未命中",
        query="Port 8080 was already in use.",
        fault_type=FaultType.PORT_CONFLICT,
        expected_knowledge_titles=["端口冲突排查手册"],
        k=3,
    )

    result = evaluate_logmind_rag_case(
        case,
        retriever=lambda *_args, **_kwargs: [
            KnowledgeRef(
                title="连接失败排查手册",
                source="docs/knowledge/connection_failure.md",
                snippet="Connection refused.",
            )
        ],
    )

    assert not result.passed
    assert result.retrieved_titles == ["连接失败排查手册"]
    assert result.hit_titles == []
    assert result.recall == 0.0
    assert any("rag hit count too low" in issue for issue in result.issues)


def test_evaluate_logmind_rag_cases_fixture_passes() -> None:
    cases = load_logmind_rag_eval_cases(RAG_FIXTURE_PATH)
    title_by_fault_type = {
        FaultType.PORT_CONFLICT: "端口冲突排查手册",
        FaultType.CONNECTION_FAILURE: "连接失败排查手册",
        FaultType.GATEWAY_5XX: "网关 5xx 错误排查手册",
        FaultType.TIMEOUT: "超时问题排查手册",
        FaultType.RESOURCE_EXHAUSTION: "资源耗尽排查手册",
        FaultType.CONFIGURATION_ERROR: "配置错误排查手册",
        FaultType.PERMISSION_AND_AUTH: "权限与认证失败排查手册",
        FaultType.KUBERNETES_POD_FAILURE: "Kubernetes Pod 异常排查手册",
        FaultType.CONTAINER_STARTUP_FAILURE: "容器启动失败排查手册",
        FaultType.DATABASE_SLOW_QUERY: "数据库慢查询排查手册",
        FaultType.DISK_AND_FILESYSTEM: "磁盘与文件系统排查手册",
        FaultType.TLS_DNS_NETWORK: "TLS、DNS 与网络排查手册",
    }

    def fake_retriever(_query: str, *, fault_type: FaultType, k: int) -> list[KnowledgeRef]:
        return [
            KnowledgeRef(
                title=title_by_fault_type[fault_type],
                source="docs/knowledge/fake.md",
                snippet=f"Top-{k} fake retrieval result.",
            )
        ]

    summary = evaluate_logmind_rag_cases(cases, retriever=fake_retriever)

    assert summary.failed == 0
    assert summary.pass_rate == 1.0
    assert summary.average_recall == 1.0


def test_evaluate_logmind_report_cases_fixture_passes() -> None:
    cases = load_logmind_report_eval_cases(REPORT_FIXTURE_PATH)
    summary = evaluate_logmind_report_cases(cases)

    assert len(cases) >= 40
    assert summary.failed == 0
    assert summary.pass_rate == 1.0
    assert summary.average_quality_score == 100
    assert summary.structure_complete_rate == 1.0
    assert summary.evidence_coverage_rate == 1.0
    assert summary.reference_accuracy_pass_rate == 1.0
    assert summary.fact_consistency_pass_rate == 1.0
    assert all(result.quality_score == 100 for result in summary.results)
    assert all(result.reference_accuracy_passed for result in summary.results)
    assert all(result.fact_consistency_passed for result in summary.results)


def test_evaluate_logmind_report_case_reports_missing_sections_and_evidence() -> None:
    case = LogMindReportEvalCase(
        id="bad_report",
        name="缺失章节和证据",
        input_summary="Port 8080 was already in use.",
        expected_fault_type=FaultType.PORT_CONFLICT,
        expected_min_severity=Severity.MEDIUM,
        required_evidence=["Port 8080"],
        report_markdown="""## 1. 问题概述
- 故障类型：端口冲突
- 严重等级：低
- 简要说明：服务启动失败。

## 2. 关键信息提取
- Web server failed to start.
""",
    )

    result = evaluate_logmind_report_case(case)

    assert not result.passed
    assert any("missing report sections" in issue for issue in result.issues)
    assert any("severity lower than expected" in issue for issue in result.issues)
    assert any("missing required report evidence" in issue for issue in result.issues)
    assert result.quality_score < 50


def test_evaluate_logmind_report_case_reports_unsupported_reference() -> None:
    case = LogMindReportEvalCase(
        id="unsupported_reference",
        name="编造参考知识",
        input_summary="Port 8080 was already in use.",
        expected_fault_type=FaultType.PORT_CONFLICT,
        expected_min_severity=Severity.MEDIUM,
        required_evidence=["Port 8080"],
        knowledge_refs=[
            KnowledgeRef(
                title="端口冲突排查手册",
                source="docs/knowledge/port_conflict.md",
                snippet="确认端口占用。",
            )
        ],
        report_markdown="""## 1. 问题概述
- 故障类型：端口冲突
- 严重等级：中
- 简要说明：服务启动失败。

## 2. 关键信息提取
- Port 8080 was already in use.

## 3. 可能原因分析
- 端口被其他进程占用。

## 4. 建议排查步骤
- 检查端口占用。

## 5. 修复建议
- 停止占用进程。

## 6. 后续预防建议
- 规划端口。

## 7. 参考知识
- 并不存在的排查秘籍：这是模型编造的来源。
""",
    )

    result = evaluate_logmind_report_case(case)

    assert not result.passed
    assert result.unsupported_knowledge_titles == ["并不存在的排查秘籍"]
    assert not result.reference_accuracy_passed
    assert any("unsupported knowledge references" in issue for issue in result.issues)
    assert result.quality_breakdown["references"] == 0


def test_score_logmind_report_quality_returns_breakdown() -> None:
    case = load_logmind_report_eval_cases(REPORT_FIXTURE_PATH)[0]

    breakdown = score_logmind_report_quality(case=case)

    assert breakdown == {
        "sections": 15,
        "evidence": 15,
        "causes": 15,
        "troubleshooting": 15,
        "fixes": 15,
        "prevention": 10,
        "references": 5,
        "grounding": 10,
    }
    assert sum(breakdown.values()) == 100


def test_evaluate_fact_consistency_accepts_grounded_terms() -> None:
    result = evaluate_fact_consistency(
        report_markdown="""## 1. 问题概述
- 故障类型：端口冲突
- 严重等级：中
- 简要说明：端口冲突。

## 3. 可能原因分析
- 8080 端口被旧服务占用。

## 4. 建议排查步骤
- 检查 8080 端口占用。

## 5. 修复建议
- 修改 server.port 或释放 8080 端口。
""",
        input_summary="Port 8080 was already in use.",
        knowledge_refs=[
            KnowledgeRef(
                title="端口冲突排查手册",
                source="docs/knowledge/port_conflict.md",
                snippet="可修改 server.port 或释放端口。",
            )
        ],
        required_grounding_terms=["8080", "server.port"],
    )

    assert result.passed
    assert result.grounded_terms == ["8080", "server.port"]


def test_evaluate_fact_consistency_rejects_ungrounded_terms() -> None:
    result = evaluate_fact_consistency(
        report_markdown="""## 3. 可能原因分析
- 可能是 Kubernetes 集群网络策略导致。

## 5. 修复建议
- 重建 Kubernetes 集群。
""",
        input_summary="Port 8080 was already in use.",
        knowledge_refs=[
            KnowledgeRef(
                title="端口冲突排查手册",
                source="docs/knowledge/port_conflict.md",
                snippet="确认端口占用。",
            )
        ],
        required_grounding_terms=["Kubernetes"],
    )

    assert not result.passed
    assert result.missing_from_sources == ["Kubernetes"]
    assert any("grounding terms missing from sources" in issue for issue in result.issues)


def test_evaluate_knowledge_reference_accuracy_accepts_known_title() -> None:
    result = evaluate_knowledge_reference_accuracy(
        report_markdown="""## 7. 参考知识
- 端口冲突排查手册：先确认端口占用进程。
""",
        knowledge_refs=[
            KnowledgeRef(
                title="端口冲突排查手册",
                source="docs/knowledge/port_conflict.md",
                snippet="先确认端口占用进程。",
            )
        ],
    )

    assert result.passed
    assert result.cited_titles == ["端口冲突排查手册"]
    assert result.supported_titles == ["端口冲突排查手册"]


def test_evaluate_knowledge_reference_accuracy_rejects_fabricated_title() -> None:
    result = evaluate_knowledge_reference_accuracy(
        report_markdown="""## 7. 参考知识
- 虚构 Kubernetes 权威手册：请参考该资料。
""",
        knowledge_refs=[],
    )

    assert not result.passed
    assert result.unsupported_titles == ["虚构 Kubernetes 权威手册"]
    assert any(
        "report cites knowledge references but retrieval returned no references" in issue
        for issue in result.issues
    )


def test_evaluate_logmind_golden_replay_cases_fixture_passes() -> None:
    cases = load_logmind_golden_replay_cases(GOLDEN_FIXTURE_PATH)
    summary = evaluate_logmind_golden_replay_cases(cases)

    assert len(cases) >= 2
    assert summary.failed == 0
    assert summary.pass_rate == 1.0
    assert all(result.quality_score >= result.expected_min_quality_score for result in summary.results)


def test_evaluate_logmind_golden_replay_case_reports_quality_regression() -> None:
    case = LogMindGoldenReplayCase(
        id="quality_regression",
        name="质量分退化",
        input_text="Web server failed to start. Port 8080 was already in use.",
        generated_report_markdown="""## 1. 问题概述
- 故障类型：端口冲突
- 严重等级：中
- 简要说明：服务启动失败。

## 2. 关键信息提取
- Web server failed to start.
""",
        expected_fault_type=FaultType.PORT_CONFLICT,
        expected_min_severity=Severity.MEDIUM,
        required_input_evidence=["Port 8080"],
        required_report_evidence=["Port 8080"],
        expected_min_quality_score=80,
    )

    result = evaluate_logmind_golden_replay_case(case)

    assert not result.passed
    assert result.input_passed
    assert not result.report_passed
    assert result.quality_score < result.expected_min_quality_score
    assert any("quality_score below threshold" in issue for issue in result.issues)
