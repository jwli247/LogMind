from enum import StrEnum

from pydantic import BaseModel, Field


class FaultType(StrEnum):
    UNKNOWN = "unknown"
    PORT_CONFLICT = "port_conflict"
    CONNECTION_FAILURE = "connection_failure"
    TIMEOUT = "timeout"
    GATEWAY_5XX = "gateway_5xx"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    PERMISSION_AND_AUTH = "permission_and_auth"
    CONFIGURATION_ERROR = "configuration_error"
    CONTAINER_STARTUP_FAILURE = "container_startup_failure"
    KUBERNETES_POD_FAILURE = "kubernetes_pod_failure"
    DATABASE_SLOW_QUERY = "database_slow_query"
    DISK_AND_FILESYSTEM = "disk_and_filesystem"
    TLS_DNS_NETWORK = "tls_dns_network"

    # Legacy MVP fault types kept for backward compatibility with existing records.
    DATABASE_CONNECTION = "database_connection"
    REDIS_CONNECTION = "redis_connection"
    NGINX_GATEWAY = "nginx_gateway"
    JVM_MEMORY = "jvm_memory"
    NULL_POINTER = "null_pointer"
    SQL_ERROR = "sql_error"
    CONFIG_ERROR = "config_error"
    PERMISSION_ERROR = "permission_error"
    DOCKER_ERROR = "docker_error"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class KnowledgeRef(BaseModel):
    title: str = Field(description="知识来源标题，例如故障手册、历史案例或文档名称")
    source: str | None = Field(default=None, description="知识来源地址或标识")
    snippet: str | None = Field(default=None, description="被引用的关键片段")


class SimilarIncidentRef(BaseModel):
    record_id: str = Field(description="历史诊断记录 ID")
    fault_type: FaultType = Field(description="历史诊断故障类型")
    severity: Severity = Field(description="历史诊断严重等级")
    summary: str = Field(description="历史诊断摘要")
    created_at: str = Field(description="历史诊断创建时间")
    thread_id: str | None = Field(default=None, description="历史诊断所属会话 ID")


class AgentTraceStep(BaseModel):
    step: str = Field(description="Agent 执行步骤标识")
    title: str = Field(description="步骤名称")
    status: str = Field(default="success", description="步骤状态")
    detail: str | None = Field(default=None, description="步骤说明")
    metadata: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict,
        description="步骤相关的结构化元数据",
    )


class DiagnosisQualityEvaluation(BaseModel):
    quality_score: int = Field(ge=0, le=100, description="诊断报告质量分，0 到 100")
    quality_breakdown: dict[str, int] = Field(
        default_factory=dict,
        description="诊断报告质量分项",
    )
    reference_accuracy_passed: bool = Field(description="RAG 引用准确性是否通过")
    cited_knowledge_titles: list[str] = Field(
        default_factory=list,
        description="报告中实际引用的知识标题",
    )
    unsupported_knowledge_titles: list[str] = Field(
        default_factory=list,
        description="未能匹配到实际 knowledge_refs 的引用标题",
    )
    fact_consistency_passed: bool = Field(
        default=True,
        description="事实一致性校验是否通过",
    )
    grounded_terms: list[str] = Field(
        default_factory=list,
        description="已在证据来源和报告分析中同时命中的关键术语",
    )
    ungrounded_terms: list[str] = Field(
        default_factory=list,
        description="未能完成证据回溯的关键术语",
    )
    issues: list[str] = Field(default_factory=list, description="诊断质量评估发现的问题")


class DiagnosisReport(BaseModel):
    summary: str = Field(description="问题摘要")
    fault_type: FaultType = Field(default=FaultType.UNKNOWN, description="故障类型")
    severity: Severity = Field(default=Severity.MEDIUM, description="严重等级")
    affected_component: str | None = Field(default=None, description="受影响组件")

    key_evidence: list[str] = Field(default_factory=list, description="关键日志证据")
    possible_causes: list[str] = Field(default_factory=list, description="可能原因")
    troubleshooting_steps: list[str] = Field(default_factory=list, description="建议排查步骤")
    fix_suggestions: list[str] = Field(default_factory=list, description="修复建议")
    prevention_suggestions: list[str] = Field(default_factory=list, description="后续预防建议")

    confidence: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="诊断置信度，取值范围 0 到 1",
    )
    knowledge_refs: list[KnowledgeRef] = Field(
        default_factory=list,
        description="后续 RAG 或历史案例检索命中的知识引用",
    )
    agent_trace: list[AgentTraceStep] = Field(
        default_factory=list,
        description="Agent 诊断执行轨迹",
    )
    similar_incidents: list[SimilarIncidentRef] = Field(
        default_factory=list,
        description="相似历史诊断案例引用",
    )
    quality_evaluation: DiagnosisQualityEvaluation | None = Field(
        default=None,
        description="诊断报告质量评估结果",
    )


class DiagnosisRecord(DiagnosisReport):
    id: str = Field(description="诊断记录 ID")
    thread_id: str | None = Field(default=None, description="会话 ID")
    user_id: str | None = Field(default=None, description="用户 ID")
    report_markdown: str = Field(description="Markdown 格式诊断报告")
    model: str | None = Field(default=None, description="本次诊断使用的模型")
    created_at: str = Field(description="诊断记录创建时间，ISO 8601 格式")


class DiagnosisDailyCount(BaseModel):
    date: str = Field(description="统计日期，格式为 YYYY-MM-DD")
    count: int = Field(description="当天诊断记录数量")


class DiagnosisStats(BaseModel):
    total: int = Field(description="诊断记录总数")
    by_fault_type: dict[str, int] = Field(default_factory=dict, description="按故障类型统计")
    by_severity: dict[str, int] = Field(default_factory=dict, description="按严重等级统计")
    daily_counts: list[DiagnosisDailyCount] = Field(default_factory=list, description="按日期统计趋势")


class AgentTraceStepStats(BaseModel):
    step: str = Field(description="Agent 执行步骤标识")
    title: str = Field(description="Agent 执行步骤名称")
    total: int = Field(description="该步骤出现次数")
    success: int = Field(default=0, description="该步骤成功次数")
    failed: int = Field(default=0, description="该步骤失败次数")
    skipped: int = Field(default=0, description="该步骤跳过次数")
    other: int = Field(default=0, description="其他状态次数")


class AgentObservabilitySummary(BaseModel):
    total_records: int = Field(description="参与统计的诊断记录数")
    records_with_trace: int = Field(description="包含 Agent 执行轨迹的诊断记录数")
    trace_coverage_rate: float = Field(description="诊断记录中包含执行轨迹的比例")
    total_trace_steps: int = Field(description="Agent 执行步骤总数")
    average_trace_steps_per_record: float = Field(description="平均每条诊断记录的执行步骤数")
    failed_trace_records: int = Field(description="包含失败执行步骤的诊断记录数")
    failed_trace_steps: int = Field(description="失败执行步骤总数")
    knowledge_hit_records: int = Field(description="命中知识库引用的诊断记录数")
    knowledge_hit_rate: float = Field(description="知识库引用命中率")
    similar_incident_hit_records: int = Field(description="命中相似历史案例的诊断记录数")
    similar_incident_hit_rate: float = Field(description="相似历史案例命中率")
    quality_evaluated_records: int = Field(description="包含质量评估的诊断记录数")
    average_quality_score: float = Field(description="平均诊断报告质量分")
    average_runtime_ms: float = Field(description="平均 Agent 诊断运行耗时，单位毫秒")
    p95_runtime_ms: float = Field(default=0.0, description="Agent 诊断运行耗时 p95，单位毫秒")
    average_model_latency_ms: float = Field(description="平均模型生成耗时，单位毫秒")
    p95_model_latency_ms: float = Field(default=0.0, description="模型生成耗时 p95，单位毫秒")
    token_usage_records: int = Field(default=0, description="包含 token 用量元数据的诊断记录数")
    total_input_tokens: int = Field(default=0, description="累计输入 token 数")
    total_output_tokens: int = Field(default=0, description="累计输出 token 数")
    total_tokens: int = Field(default=0, description="累计总 token 数")
    average_total_tokens: float = Field(default=0.0, description="平均每次诊断总 token 数")
    total_estimated_cost_usd: float = Field(default=0.0, description="累计估算 token 成本，单位美元")
    average_estimated_cost_usd: float = Field(default=0.0, description="平均单次诊断估算 token 成本，单位美元")
    low_quality_records: int = Field(description="低于质量阈值的诊断记录数")
    reference_accuracy_failed_records: int = Field(description="RAG 引用准确性失败的诊断记录数")
    step_stats: list[AgentTraceStepStats] = Field(default_factory=list, description="按步骤聚合的执行统计")
    failure_reasons: list[str] = Field(default_factory=list, description="失败步骤的复盘原因")
