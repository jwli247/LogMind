# LogMind Baseline 对比实验

本文档说明 LogMind 当前 baseline 对比实验的设计和边界。

## 对比方案

### direct_llm

只把用户日志交给模型，不接入规则分类、知识库、历史案例、结构化解析和运行观测。

当前项目没有在离线脚本中调用真实模型，所以 direct LLM 不统计生成质量数字。它主要作为能力边界 baseline，用来说明纯模型问答缺少可回归评估和诊断链路追踪。

### rag_only

只做知识库检索，不使用故障类型过滤，不召回历史案例，也不记录 Agent Trace。

这个方案用于观察普通 RAG 在不利用规则分类结果时的 Top-3 召回表现。

### agent_rag

完整 LogMind 链路，包括诊断请求识别、规则故障分类、RAG 检索、历史案例召回、结构化报告、质量评估、Agent Trace 和运行观测。

## 当前结果

运行命令：

```powershell
uv run python scripts/compare_logmind_baselines.py
```

当前结果：

```text
strategy   classification      rag_top3          report_eval      trace   observability
direct_llm -                   -                 -                no      no
rag_only   -                   22/24 (91.7%)     -                no      no
agent_rag  160/160 (100.0%)    24/24 (100.0%)    40/40 (100.0%)   yes     yes
```

## 怎么理解

这个实验不能说明 Agent-RAG 的真实模型生成质量一定优于 direct LLM，因为 direct LLM 没有在离线脚本里实际调用模型。

它能说明三件事：

- Agent-RAG 多了可回归的故障分类链路，当前 160 条分类样本通过。
- Agent-RAG 会把故障类型作为 RAG 过滤条件，在 24 条 RAG 样本上 Top-3 召回从普通 RAG 的 91.7% 提升到 100%。
- Agent-RAG 有 40 条离线报告评估样本，会检查报告结构、关键证据、RAG 引用准确性和事实一致性。
- Agent-RAG 具备 Trace、质量评估、p95 延迟、token 用量和成本观测，普通问答和普通 RAG 不具备这些工程能力。

## 面试说法

> 我做了一个离线 baseline 对比，不直接声称模型生成质量提升。对比重点放在可复现的工程指标上：普通 RAG 不使用故障类型过滤时，24 条 RAG 样本 Top-3 命中 22 条；完整 Agent-RAG 会先做规则分类，再用 fault_type 过滤知识库，Top-3 命中 24 条。同时 Agent-RAG 还有 Trace、质量评估、p95 延迟和 token 成本观测，这些是普通问答链路没有的。
