# LogMind 评估数据来源说明

本文档说明 LogMind 当前评估样本的来源、用途和边界，避免把本地回归测试误讲成大规模公开 benchmark。

## 1. 本地回归评估集

文件：`tests/fixtures/logmind_eval_cases.json`

规模：

- 80 条脱敏日志/请求样本
- 12 类常见后端和运维故障，每类 6 条
- 8 条普通对话边界样本

用途：

- 验证诊断请求识别是否正确。
- 验证规则分类器是否把日志分到期望 `FaultType`。
- 验证样本中关键证据没有丢失。
- 每次改分类规则、prompt 或知识库后做回归测试。

边界：

- 这些样本是项目内构造的回归样本，适合说明工程可回归能力。
- 不能把它说成真实线上准确率，也不能说成大规模泛化能力。

面试说法：

> 这 80 条主要是 regression eval，用来保证我改规则和 prompt 后不退化。它的价值是可复现和可回归，不是证明线上泛化能力。

## 2. 公开日志小样本集

文件：`tests/fixtures/logmind_public_log_eval_cases.json`

规模：

- 40 条公开日志风格小样本
- 覆盖 Apache、OpenSSH、HDFS、OpenStack、ZooKeeper、BGL 等来源

主要来源：

- LogHub / LogPAI：`https://github.com/logpai/loghub`

用途：

- 补充验证 LogMind 对公开日志风格的基础识别能力。
- 发现项目内构造样本没有覆盖的真实表达，比如 `Failed password`、`Connection closed`、`session timed out`。
- 把公开日志样本中的 bad case 反向沉淀进分类规则和 eval。

边界：

- 当前只是小样本抽样和脱敏改写，不是完整跑 LogHub 全量数据。
- 部分公开日志只有异常模式，没有直接的业务故障标签，所以需要人工粗标注。
- 适合简历里写“引入公开日志小样本做补充评估”，不适合写成“在 LogHub benchmark 上达到 xx%”。

面试说法：

> 我没有只用自己构造的样本，也补了一组公开日志风格样本。它不是全量 benchmark，而是用来检查项目对外部日志表达的适应性。比如 OpenSSH 的 Failed password、ZooKeeper 的 session timed out 这类表达，就是通过这组样本反向补进分类规则的。

## 3. 外部人工标注案例集

文件：`tests/fixtures/logmind_external_annotated_cases.json`

规模：

- 40 条外部案例样本
- 每条包含 `dataset`、`source_url`、`annotation_note`

主要来源：

- Spring Boot 官方文档：`https://docs.spring.io/spring-boot/reference/web/web-server.html`
- MySQL 官方文档：`https://dev.mysql.com/doc/refman/8.4/en/problems-connecting.html`
- Kubernetes 官方文档：`https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/`
- Docker 官方文档：`https://docs.docker.com/reference/cli/docker/container/run/`
- Nginx 官方文档：`https://nginx.org/en/docs/http/ngx_http_proxy_module.html`

用途：

- 验证项目对常见官方故障场景的覆盖。
- 让每条样本都有来源说明，面试时能解释样本不是完全凭空编的。
- 补充端口占用、数据库认证失败、Nginx 502/504、JVM OOM、Kubernetes Pod 异常、Docker 容器退出、DNS 解析失败等典型场景。

边界：

- 这些样本是根据官方文档和公开问题场景人工构造的脱敏日志，不是真实生产日志原文。
- 主要验证分类和诊断入口，不直接验证 LLM 生成质量。

面试说法：

> 外部人工标注案例集是我根据官方文档和公开故障场景整理的，每条都记录 source_url 和标注说明。它的作用是让评估不只停留在项目内自造样本，同时又避免直接保存隐私日志。

## 4. RAG Top-3 召回评估

文件：`tests/fixtures/logmind_rag_eval_cases.json`

规模：

- 24 条 RAG Top-3 召回样本
- 覆盖 12 类运维 Runbook

用途：

- 验证给定日志和 `fault_type` 后，Top-3 检索结果中是否包含期望知识标题。
- 回答面试高频问题：“RAG 召回率怎么评估？”

边界：

- 当前知识库规模较小，所以 Top-3 命中率高是合理的。
- 后续知识库扩大后，应增加 recall@1、recall@3、recall@5 对比，并加入 rerank 或混合检索。

面试说法：

> RAG 不是只看能不能返回内容，我做了 Top-k 命中评估。每条 case 标注期望知识标题，脚本会检查 Top-3 里有没有召回对应 Runbook。当前知识库规模较小，所以这个指标主要用于回归验证；后续知识库扩大后会继续比较 recall@1、recall@3 和 recall@5。

## 5. 批量报告质量评估

文件：`tests/fixtures/logmind_report_eval_cases.json`

规模：

- 40 条报告评估样本
- 基于外部人工标注案例集生成标准诊断报告
- 覆盖报告结构、关键证据、知识引用和事实一致性

用途：

- 验证诊断报告是否稳定包含固定 7 个章节。
- 验证“关键信息提取”里是否保留原始日志证据。
- 验证“参考知识”里引用的标题是否来自本次真实检索到的 `knowledge_refs`。
- 验证关键原因和修复建议能否回溯到用户输入或知识库片段。
- 为后续真实模型抽样评估提供同一套打分规则。

边界：

- 当前 40 条是离线回归样本，主要用于验证报告评估器和输出契约。
- 它不等于真实线上模型泛化结果，也不能说成大规模 benchmark。
- 如果要评估真实模型生成质量，应运行 `scripts/run_logmind_live_report_eval.py --run-live-model` 做抽样评估。

面试说法：

> 报告评估不是只看模型写得顺不顺，而是检查结构、证据、引用和事实一致性。当前 40 条报告样本用于离线回归，保证评估器和 prompt 契约稳定；真实模型效果会单独用抽样脚本跑，避免把标准答案评估误讲成模型泛化能力。

## 6. 真实模型抽样评估入口

文件：`scripts/run_logmind_live_report_eval.py`

默认 dry-run：

```powershell
uv run python scripts/run_logmind_live_report_eval.py --sample-size 3
```

真正调用模型：

```powershell
uv run python scripts/run_logmind_live_report_eval.py --sample-size 5 --run-live-model
```

用途：

- 先执行和实际 Agent 一致的规则分类和 Top-3 知识检索，再调用当前配置的真实 LLM。
- 使用本次真实检索到的知识引用评估报告质量，统计分类命中、质量分、失败原因、端到端延迟、模型延迟和 token 用量。
- 避免离线标准报告指标和真实模型生成指标混在一起。

真实模型运行建议先用 5 条样本检查模型配置和报告格式，再使用 30 条样本生成简历指标。样本数不大时，p95 只能作为当前模型和当前环境下的参考，不能描述为线上 SLA。

## 7. 离线评估管道耗时基准

文件：`scripts/benchmark_logmind_eval_pipeline.py`

运行命令：

```powershell
uv run python scripts/benchmark_logmind_eval_pipeline.py
```

用途：

- 统计分类评估、RAG Top-3 评估和报告质量评估的通过率、失败率、平均耗时、p50 和 p95。
- 作为本地回归评估管道的性能基准，用于发现规则、检索或评估逻辑的明显退化。

边界：

- 这个脚本不调用真实 LLM，测量的是本地离线评估管道，不是一次完整诊断请求的端到端延迟。
- 真实模型端到端延迟、token 用量和估算成本应以第 6 节的 live eval 输出为准。

## 8. 当前可复现结果

运行命令：

```powershell
uv run python scripts/evaluate_logmind_cases.py
```

当前结果：

```text
LogMind eval: 80/80 passed (100.0%), failed=0
LogMind report eval: 40/40 passed (100.0%), failed=0
LogMind report metrics: average_quality_score=100.0, structure_complete_rate=100.0%, evidence_coverage_rate=100.0%, reference_accuracy=100.0%, fact_consistency=100.0%
LogMind golden replay: 2/2 passed (100.0%), failed=0
LogMind RAG eval: 24/24 passed (100.0%), average_recall=100.0%, failed=0
LogMind public log eval: 40/40 passed (100.0%), failed=0
LogMind external annotated eval: 40/40 passed (100.0%), failed=0
```

简历建议写法：

> 构建 80 条本地回归评估样本、40 条公开日志小样本、40 条外部人工标注案例、40 条报告评估样本和 24 条 RAG Top-3 召回样本，覆盖常见后端与运维故障场景；通过固定评估脚本持续验证诊断入口识别、故障分类、RAG 召回、报告结构、引用准确性和事实一致性，降低规则、prompt 和知识库迭代带来的回归风险。

真实模型抽样结果见 `docs/logmind-live-eval-results.md`。该结果和离线标准报告评估分开记录，避免把固定答案的回归通过率误写成模型效果。
