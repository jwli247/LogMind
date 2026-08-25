# LogMind 知识库规范

本目录用于维护 LogMind 的 RAG 运维排障知识库。知识库面向应用服务、中间件、数据库、容器、操作系统、网络和云服务等场景，不绑定某个单一语言、框架或平台。

## 定位

知识库用于为 LogMind 提供可信、可检索、可维护的排障上下文。它不是官方文档全文镜像，而是基于官方文档、通用运维实践和后续历史案例整理出的 Runbook。

RAG 检索链路：

```text
用户日志或故障描述
    |
    v
诊断意图识别与 FaultType 分类
    |
    v
按 fault_type / domains / signals 检索知识库
    |
    v
召回相关 Runbook 片段
    |
    v
注入 LogMind Prompt
    |
    v
生成带参考依据的诊断报告
```

## 文档命名

文档按通用故障模式命名，而不是按单一技术栈命名。

第一批知识文档：

- `port_conflict.md`
- `connection_failure.md`
- `timeout.md`
- `gateway_5xx.md`
- `resource_exhaustion.md`
- `permission_and_auth.md`
- `configuration_error.md`
- `container_startup_failure.md`
- `kubernetes_pod_failure.md`
- `database_slow_query.md`
- `disk_and_filesystem.md`
- `tls_dns_network.md`

## Metadata 规范

每篇文档必须包含 YAML front matter：

```yaml
---
title: 文档标题
fault_type: port_conflict
domains:
  - application
  - container
signals:
  - address already in use
  - port is already allocated
severity_hint: medium
source_type: runbook
source_urls:
  - https://example.com/official-doc
---
```

字段说明：

- `title`：文档标题，用于知识引用展示。
- `fault_type`：故障模式，与 `FaultType` 或后续扩展分类保持一致。
- `domains`：适用技术域，例如 `application`、`database`、`cache`、`container`、`kubernetes`、`network`、`cloud_service`。
- `signals`：常见日志信号或错误关键词，用于检索增强和人工维护。
- `severity_hint`：默认严重程度参考，不代表最终诊断结论。
- `source_type`：来源类型，可选 `official_docs`、`runbook`、`historical_case`。
- `source_urls`：官方文档或可信来源链接。Runbook 内容应自行整理，不直接大段复制官方文档。

## 内容结构

每篇 Runbook 建议包含：

```markdown
## 适用场景
## 常见日志信号
## 常见原因
## 排查步骤
## 修复建议
## 预防建议
## 参考来源
```

## 编写原则

- 面向故障模式，不面向单一框架。
- 优先覆盖跨技术栈的共性排障方法。
- 不保存 API Key、密码、Token、真实生产日志等敏感信息。
- 不直接复制官方文档全文，只记录来源并整理成适合 LogMind 检索的 Runbook。
- 每篇文档控制在适合检索的长度，后续通过 chunk 切分进入向量库。

## 后续扩展

后续可以增加：

- 经人工确认的历史诊断案例。
- 按公司或项目沉淀的内部 Runbook。
- RAG 召回评测样例。
- reranker 重排能力。
- 文档版本号和最近更新时间。
