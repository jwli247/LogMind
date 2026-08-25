# LogMind 设计文档

## 1. 项目定位

LogMind 是一个面向后端开发和运维排障场景的智能日志分析 Agent 平台。

项目基于 `agent-service-toolkit` 二次开发，目标不是再做传统后台管理系统，而是聚焦在：

- 日志分析
- 异常堆栈解析
- 故障诊断
- 运维排障
- 修复建议生成
- 故障报告沉淀

当前阶段的核心目标是先构建一个可运行、可验证、可逐步扩展的 LogMind Agent，再围绕结构化诊断、历史留痕和报告管理逐步增强项目深度。

## 2. 技术栈

当前项目主要技术栈：

- Python 3.12
- uv
- LangGraph
- LangChain
- FastAPI
- Streamlit
- Pydantic
- SQLite
- OpenAI-compatible API

其中：

- LangGraph 负责 Agent 编排和多轮会话状态。
- FastAPI 负责提供后端 Agent 服务接口。
- Streamlit 负责提供本地可交互的聊天式前端。
- SQLite 用于后续诊断历史和报告数据持久化。
- OpenAI-compatible API 用于接入第三方大模型服务。

## 3. 当前架构

当前项目延续 `agent-service-toolkit` 的基本架构：

```text
Streamlit 前端
    |
    | 通过 AgentClient 调用
    v
FastAPI Agent 服务
    |
    | 根据 Agent key 路由
    v
LangGraph Agent
    |
    | 调用模型
    v
OpenAI-compatible LLM
```

当前 LogMind 相关文件：

- `src/agents/logmind.py`：LogMind Agent 实现。
- `src/agents/agents.py`：Agent 注册表，负责暴露 `logmind`。
- `src/streamlit_app.py`：Streamlit 前端，负责 Agent 选择、欢迎语和聊天交互。
- `src/core/llm.py`：模型工厂，负责根据配置创建模型实例。
- `src/core/settings.py`：配置读取，负责模型、数据库和运行环境配置。

## 4. LogMind Agent 工作流程

当前 MVP 的工作流程如下：

```text
用户输入日志、异常堆栈或故障描述
    |
    v
Streamlit 前端收集输入
    |
    v
AgentClient 将消息发送到后端服务
    |
    v
后端根据默认 Agent 或用户选择路由到 logmind
    |
    v
logmind 合并当前输入和历史对话
    |
    v
注入 LogMind 系统提示词
    |
    v
调用 OpenAI-compatible 模型
    |
    v
返回 Markdown 故障诊断报告
```

LogMind 当前要求模型始终使用简体中文，并按照固定结构输出：

```markdown
## 1. 问题概述
## 2. 关键信息提取
## 3. 可能原因分析
## 4. 建议排查步骤
## 5. 修复建议
## 6. 后续预防建议
```

## 5. 当前 MVP 能力

当前版本已经完成：

- 新增独立 `logmind` Agent。
- 使用 LangGraph `@entrypoint()` 实现 Agent 入口。
- 支持多轮对话历史。
- 通过 `get_model(config["configurable"].get("model", settings.DEFAULT_MODEL))` 获取模型。
- 注册到后端 Agent 列表。
- 将默认 Agent 切换为 `logmind`。
- Streamlit 前端支持选择 `logmind`。
- 为 `logmind` 增加中文欢迎语。
- 对前端主要用户可见文案进行中文化。
- 通过 `/info` 验证后端 Agent 注册。
- 通过 Spring Boot 端口占用日志验证基础排障效果。

当前已验证的典型场景：

- Spring Boot 启动失败。
- Web Server 无法启动。
- `8080` 端口被占用。
- 输出 Windows/Linux/macOS/Docker 等常见排查建议。
- 提醒生产环境谨慎操作和敏感信息脱敏。

## 6. 当前边界

当前版本刻意保持轻量，没有接入以下能力：

- RAG 知识库。
- ChromaDB。
- MySQL、Redis、Nginx 等真实环境检测工具。
- 日志文件上传。
- 诊断结果入库。
- 报告导出。
- 历史诊断查询。
- 故障统计分析。

这样做的好处是先把 Agent 注册、模型调用、前端交互和基础诊断链路跑通，降低早期改动风险。

## 7. 后续计划

### 阶段一：结构化诊断报告

设计诊断结果结构，例如：

- `summary`：问题摘要
- `fault_type`：故障类型
- `severity`：严重等级
- `affected_component`：影响组件
- `key_evidence`：关键证据
- `possible_causes`：可能原因
- `troubleshooting_steps`：排查步骤
- `fix_suggestions`：修复建议
- `prevention_suggestions`：预防建议

目标是让 LogMind 不只是输出 Markdown，而是具备可保存、可查询、可展示的数据结构。

### 阶段二：故障分类能力

建立常见后端故障分类体系，例如：

- 端口占用
- 数据库连接失败
- Redis 连接超时
- Nginx 502/504
- Docker 容器启动失败
- JVM OOM
- NullPointerException
- SQL 语法错误
- 配置文件错误
- 权限或路径问题

可以先用规则和提示词组合实现，再逐步增强。

### 阶段三：诊断历史持久化

基于 SQLite 保存诊断记录，例如：

- 用户 ID
- 会话 ID
- 输入摘要
- 故障类型
- 严重等级
- 诊断报告
- 模型名称
- 创建时间

目标是形成故障复盘和报告沉淀能力。

### 阶段四：前端诊断工作台

在 Streamlit 中增加：

- 历史诊断列表
- 故障类型筛选
- 严重等级标签
- 报告详情页
- Markdown 报告复制
- 标题字号优化
- 常见日志样例入口

目标是让项目从聊天界面升级为更像运维诊断工具的工作台。

### 阶段五：知识库和工具增强

在基础链路稳定后，再考虑：

- RAG 知识库
- 常见故障手册
- 历史案例检索
- 日志文件上传
- 本地端口检测工具
- MySQL/Redis 连通性检测工具
- Docker 容器状态分析

这些能力应逐步接入，避免早期一次性复杂化。

## 8. 适合写进简历的技术点

当前 MVP 可写：

- 基于 LangGraph `@entrypoint()` 扩展独立智能 Agent，实现多轮日志分析与故障诊断能力。
- 基于 FastAPI Agent 服务注册机制，将 LogMind 接入统一 Agent 路由，并通过 `/info` 暴露 Agent 元信息。
- 基于 Streamlit 构建日志排障交互界面，支持 Agent 选择、流式输出和中文诊断报告展示。
- 接入 OpenAI-compatible API，实现模型服务解耦，支持第三方大模型配置。
- 设计面向运维排障场景的系统提示词，规范输出问题概述、关键信息、原因分析、排查步骤、修复建议和预防建议。

后续增强后可写：

- 设计结构化诊断报告 Schema，将 LLM 输出沉淀为可保存、可查询、可展示的故障诊断数据。
- 构建常见后端故障分类体系，支持端口冲突、数据库连接失败、Redis 超时、Nginx 网关错误、JVM OOM 等场景自动归因。
- 基于 SQLite 实现诊断历史持久化，支持故障复盘、历史查询和报告管理。
- 实现智能运维诊断工作台，支持报告详情展示、故障类型筛选、严重等级标记和 Markdown 报告生成。

## 9. 推荐项目叙事

简历或面试中可以这样描述项目方向：

> LogMind 是一个面向后端开发和运维排障场景的智能日志分析 Agent 平台，基于 LangGraph、FastAPI 和 Streamlit 构建。项目在通用 Agent 服务框架上扩展了独立的日志诊断 Agent，支持对异常堆栈和运行日志进行关键信息提取、故障原因分析、排查步骤生成和修复建议输出。后续围绕结构化诊断报告、故障分类、历史留痕和报告工作台持续增强，目标是形成可复盘、可沉淀的智能运维排障系统。

当前阶段不要把项目包装得过满。更合适的说法是：已经完成 MVP 链路，正在逐步建设结构化诊断和诊断历史能力。


## 10. 前后端与 Agent 职责划分

当前 LogMind 已形成“规则分类器 + LLM 诊断”的混合架构。规则分类器负责对高频、特征明显的故障进行稳定识别，LLM 负责结合上下文生成自然语言诊断报告。

整体链路如下：

```text
用户输入日志、异常堆栈或故障描述
    |
    v
Streamlit 前端收集输入并发送请求
    |
    v
FastAPI 后端根据 Agent key 路由到 logmind
    |
    v
LogMind Agent 合并历史消息并调用规则分类器
    |
    v
规则分类器返回 FaultType
    |
    v
LogMind 将初步故障类型注入系统提示词
    |
    v
LLM 生成结构化 Markdown 诊断报告
    |
    v
前端展示诊断结果


## 11. 当前诊断闭环

当前 LogMind 已经从基础 Prompt 型 Agent，演进为具备完整 MVP 闭环的智能日志诊断系统。

当前链路如下：

```text
用户输入日志或故障描述
    |
    v
Streamlit 前端发送请求
    |
    v
LogMind Agent 判断是否为诊断请求
    |
    |-- 非诊断请求：自然回复，不进入诊断模板，不写入诊断历史
    |
    |-- 诊断请求：进入故障分析流程
            |
            v
        规则分类器识别 FaultType
            |
            v
        分类结果注入系统提示词
            |
            v
        LLM 生成 Markdown 诊断报告
            |
            v
        保存 diagnosis_records SQLite 诊断历史
            |
            v
        前端展示诊断报告