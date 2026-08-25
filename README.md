# LogMind 日志排障 Agent

LogMind 是一个面向后端开发、运维排障和日志分析场景的 AI Agent 项目。它不是简单的聊天机器人，而是围绕“用户提交日志，系统给出可追踪诊断报告”构建了一条完整链路：日志脱敏、诊断意图识别、故障类型分类、RAG 知识检索、历史案例召回、结构化报告生成、质量评估、Agent trace 记录和前端运行观测。

这个项目的定位是校招、实习、初中级 AI 应用开发、Java/Python 后端转 AI 应用方向的简历项目。重点展示 AI 应用工程能力，而不是追求大厂 Agent Platform 级别的复杂基础设施。

## 核心链路

```text
日志输入 / log 文件上传
        |
        v
敏感信息脱敏
        |
        v
诊断请求识别
        |
        +-- 非诊断请求 -> 受边界约束的普通 LLM 回复
        |
        v
规则分类器识别故障类型
        |
        v
RAG 检索静态运维知识库
        |
        v
SQLite 召回相似历史诊断案例
        |
        v
LLM 生成结构化 Markdown 诊断报告
        |
        v
报告解析 + 质量评估 + 事实一致性检查
        |
        v
保存诊断历史、引用、相似案例、trace 和质量结果
        |
        v
前端展示最近诊断、完整报告、质量评估和运行观测
```

## Agent 项目亮点

1. **场景明确**

   LogMind 聚焦日志排障，不做泛泛的通用聊天。输入是日志、异常堆栈或故障现象，输出是结构化诊断报告，方便面试时讲清楚业务边界和质量标准。

2. **不是纯 LLM 套壳**

   系统先用规则分类器识别高确定性的故障类型，再把分类结果、知识库片段和历史案例交给 LLM。这样比完全依赖模型自由判断更稳定，也更容易测试。

3. **RAG 和动态经验分离**

   静态知识库来自 `docs/knowledge/*.md`，用于提供通用排障 Runbook。动态经验来自 SQLite 中的历史诊断记录，后续相同故障类型会召回相似案例。两者来源不同，作用也不同。

4. **可追踪 Agent Trace**

   每次诊断都会记录 `agent_trace`，包括诊断意图识别、故障分类、知识库检索、历史案例召回、模型生成、结构化解析、质量评估和记录保存。每个实际工具步骤会保留 `tool_name`、输入输出摘要、状态和耗时，排查效果不好时可以定位到具体工具和失败原因。

5. **Eval 质量评估**

   项目包含分类评估、报告结构评估、RAG 引用准确性评估、事实一致性评估和 golden replay。每次改 prompt、分类规则或知识库后，可以跑评估脚本做回归验证。

6. **运行观测**

   前端统计页展示 trace 覆盖率、知识命中率、历史案例命中率、平均质量分、失败步骤、平均诊断耗时和平均模型耗时。这个部分体现的是 Agent 工程里的可观测性和延迟意识。

## 技术栈

- Python
- LangGraph / LangChain
- FastAPI
- Streamlit
- SQLite
- Chroma
- Pydantic
- pytest / ruff

## 关键目录

```text
src/agents/logmind.py              # LogMind Agent 主流程
src/agents/logmind_classifier.py   # 诊断意图识别和规则分类器
src/core/knowledge_base.py         # RAG 知识库加载、构建和检索
src/core/diagnosis_store.py        # SQLite 诊断历史和动态经验存储
src/core/logmind_eval.py           # 分类、报告、引用、事实一致性评估
src/core/logmind_tooling.py        # Agent 工具执行、失败降级和 trace 统一封装
src/core/agent_observability.py    # Agent 运行观测聚合
src/core/sensitive_data.py         # 日志敏感信息脱敏
src/core/log_file.py               # log/txt 文件预处理
src/streamlit_app.py               # 前端聊天、诊断历史、质量评估和运行观测
docs/knowledge/                   # 运维排障知识库
tests/fixtures/                   # Eval 和 golden replay 测试集
scripts/evaluate_logmind_cases.py # 一键运行 LogMind 评估
scripts/benchmark_logmind_eval_pipeline.py # 离线评估管道耗时基准
scripts/run_logmind_live_report_eval.py # 真实模型报告质量、延迟与成本抽样
```

## 本地运行

先准备环境变量，至少需要一个可用的 LLM API Key。

```powershell
cd LogMind
copy .env.example .env
```

安装依赖：

```powershell
uv sync --frozen
```

构建知识库：

```powershell
uv run python scripts\build_knowledge_base.py
```

启动后端服务：

```powershell
uv run python src\run_service.py
```

另开一个终端启动前端：

```powershell
uv run streamlit run src\streamlit_app.py
```

默认访问：

- Streamlit 前端：`http://localhost:8501`
- FastAPI 服务：`http://localhost:8080`
- API 文档：`http://localhost:8080/docs`

## 评估和测试

运行 LogMind 评估：

```powershell
uv run python scripts\evaluate_logmind_cases.py
```

运行离线评估管道基准，输出分类、RAG 和报告评估的平均耗时、p50、p95 与失败率：

```powershell
uv run python scripts\benchmark_logmind_eval_pipeline.py
```

默认只预览真实模型报告评估，不会发起模型调用：

```powershell
uv run python scripts\run_logmind_live_report_eval.py --sample-size 3
```

确认模型配置和 token 单价配置正确后，调用真实模型生成可写入简历的质量、延迟、token 和成本指标：

```powershell
uv run python scripts\run_logmind_live_report_eval.py --sample-size 30 --run-live-model
```

当前评估覆盖：

- 80 条脱敏日志/请求评估样本
- 12 类常见后端和运维故障
- 8 条普通对话边界样本
- 40 条公开日志小样本
- 40 条外部人工标注案例
- 40 条批量报告质量评估样本
- 24 条 RAG Top-3 知识召回评估样本
- 诊断意图识别
- 故障分类
- 报告结构完整性
- 关键证据覆盖
- RAG 引用准确性
- 事实一致性
- golden replay 回归

运行核心测试：

```powershell
uv run pytest -q tests\agents\test_logmind.py tests\agents\test_logmind_classifier.py tests\core\test_logmind_eval.py tests\core\test_agent_observability.py tests\core\test_diagnosis_parser.py tests\core\test_diagnosis_store.py tests\core\test_diagnosis_export.py tests\core\test_log_file.py tests\core\test_sensitive_data.py tests\service\test_service.py tests\schema\test_diagnosis.py tests\app\test_streamlit_app.py
```

代码检查：

```powershell
uv run ruff check src tests
```

## 技术取舍

这些取舍是面试里最容易被追问的部分：

- **规则分类器 + LLM**：规则负责端口冲突、OOM、连接失败这类高确定性故障入口，LLM 负责综合分析和生成排查建议。
- **静态知识库 + 动态历史案例**：`docs/knowledge` 保存稳定 Runbook，SQLite 诊断历史保存运行过程中沉淀的动态经验。
- **RAG top-k=3**：当前知识库规模不大，3 条可以兼顾上下文覆盖和噪声控制；后续可用 recall@k 对比 k=1、3、5。
- **Baseline 对比**：离线对比普通 RAG 和 Agent-RAG。普通 RAG 不使用故障类型过滤时，24 条 RAG 样本 Top-3 命中 22 条；Agent-RAG 使用规则分类结果做过滤后命中 24 条。
- **SQLite**：本地演示和简历项目优先保证可运行、可复盘；生产化可替换为 PostgreSQL 或 MySQL。
- **Chroma**：适合本地 RAG 原型，部署轻量；生产化可换 Milvus、Qdrant 或云向量库。
- **Eval 和 trace 优先于堆功能**：项目重点不是工具越多越好，而是能证明诊断链路稳定、可追踪、可回归。

更完整的面试追问回答见 [docs/logmind-interview-qna.md](docs/logmind-interview-qna.md)。
代码阅读顺序和面试问题总纲见 [docs/logmind-study-and-interview-map.md](docs/logmind-study-and-interview-map.md)。

## 面试演示建议

建议准备 2 到 3 个日志样例：

1. Spring Boot 端口冲突：`Port 8080 was already in use`
2. MySQL 连接失败：`Access denied for user` 或 `Communications link failure`
3. JVM OOM：`java.lang.OutOfMemoryError`

演示顺序：

1. 在聊天框粘贴日志或上传 `.log/.txt` 文件。
2. 展示生成的结构化诊断报告。
3. 打开最近诊断，展示完整报告、参考知识、相似历史案例和 Agent trace。
4. 打开质量评估，说明它会检查引用准确性和事实一致性。
5. 打开诊断统计，展示 Agent 运行观测，包括 trace 覆盖率、质量分、命中率和耗时。
6. 最后运行 `scripts/evaluate_logmind_cases.py`，展示项目有可回归的 Eval。

如果被追问日志切片、召回率、top-k、延迟、token 成本、bad case 处理，优先参考 [docs/logmind-interview-qna.md](docs/logmind-interview-qna.md)。

## 可以写进简历的表述

> 基于 LangGraph、FastAPI、Streamlit、SQLite 和 Chroma 实现面向运维日志排障的 LogMind Agent，支持日志脱敏、诊断意图识别、规则故障分类、RAG 运维知识检索、历史诊断案例召回、结构化诊断报告生成、Agent trace 记录和质量评估。构建分类评估、RAG 引用准确性、事实一致性和 golden replay 测试集，用于回归验证诊断链路稳定性，并在前端展示诊断历史、参考知识、质量结果和运行观测指标。

可量化版本：

> 构建 80 条本地回归评估样本、40 条公开日志小样本、40 条外部人工标注案例、40 条报告质量评估样本和 24 条 RAG Top-3 召回样本，覆盖端口冲突、连接失败、网关 5xx、超时、资源耗尽、配置错误、权限认证、Kubernetes Pod 异常、容器启动失败、数据库慢查询、磁盘文件系统和 TLS/DNS 网络异常等常见场景；离线评估中诊断入口识别和故障分类通过 160/160，普通 RAG Top-3 命中 22/24，Agent-RAG Top-3 命中 24/24，报告结构完整率、关键证据覆盖率、RAG 引用准确性和事实一致性均为 100%。

真实模型抽样结果：在 30 条外部人工标注案例上，Agent-RAG 报告通过 28/30，故障分类准确率 100.0%，平均质量分 99.7，结构完整率和事实一致性为 100.0%，RAG 引用准确性为 93.3%，端到端 p95 耗时为 27.4s，平均总 Token 为 2170。结果和边界见 [docs/logmind-live-eval-results.md](docs/logmind-live-eval-results.md)。

评估数据来源和边界见 [docs/logmind-eval-datasets.md](docs/logmind-eval-datasets.md)。公开日志和外部标注样本用于补充验证，不等同于大规模公开 benchmark。
Baseline 对比见 [docs/logmind-baseline-comparison.md](docs/logmind-baseline-comparison.md)。

## 当前边界和后续优化

当前版本适合作为简历和面试演示项目，但还不是完整生产级 Agent 平台。主要边界：

- 相似历史案例目前按故障类型和时间召回，后续可升级为 embedding 语义相似检索。
- 上传日志当前按一次输入整体预处理，还没有完整的时间窗口、trace_id 或异常堆栈级日志切片。
- Eval 数据集已覆盖 80 条本地回归样本、40 条公开日志小样本、40 条外部人工标注案例、40 条报告质量评估样本和 24 条 RAG 召回样本，后续可以继续补充更多真实线上 bad case。
- 每次诊断会记录工具执行耗时；真实模型抽样脚本会在供应商返回 token 用量且配置单价后统计 token 成本。
- 已有本地权限配置和用户隔离参数，生产化还需要更完整的认证、权限、限流和部署方案。

后续最有价值的优化：

1. 为历史案例增加 embedding 检索和混合排序。
2. 继续补充真实线上 bad case，并周期性运行真实模型抽样评估观察 p95 延迟和 token 成本。
3. 增加日志切片策略，支持时间窗口、trace_id 和异常堆栈聚合。
4. 接入 LangSmith、Langfuse 或 OpenTelemetry 做跨请求的长期观测。
5. 最后统一前端视觉和演示截图。
