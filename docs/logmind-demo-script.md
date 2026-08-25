# LogMind 面试演示脚本

这份脚本用于校招、实习、初中级 AI 应用开发、Java/Python 后端转 AI 应用方向。目标不是把项目吹成生产级平台，而是稳定讲清楚：LogMind 已经具备一个完整 Agent 应用应有的核心闭环。

## 演示前检查

1. 确认 `.env` 中至少配置了一个可用模型。
2. 确认知识库已构建：

   ```powershell
   uv run python scripts\build_knowledge_base.py
   ```

3. 跑一次评估，确保核心链路没有退化：

   ```powershell
   uv run python scripts\evaluate_logmind_cases.py
   ```

4. 启动后端：

   ```powershell
   uv run python src\run_service.py
   ```

5. 启动前端：

   ```powershell
   uv run streamlit run src\streamlit_app.py
   ```

## 推荐演示日志

### Case 1：端口冲突

```text
APPLICATION FAILED TO START
Web server failed to start. Port 8080 was already in use.
Action: Identify and stop the process that's listening on port 8080 or configure this application to listen on another port.
```

重点看：

- 是否识别为 `port_conflict`
- 报告里是否提到端口 8080
- 参考知识是否命中端口冲突 Runbook
- Agent trace 是否包含分类、知识检索、报告生成、质量评估和保存

讲法：

> 这个 case 用来展示确定性故障识别。端口冲突有非常明确的日志证据，所以我先用规则分类器稳定识别 fault_type，再让 RAG 和 LLM 负责补充排查步骤和修复建议。

### Case 2：数据库连接失败

```text
java.sql.SQLException: Access denied for user 'app_user'@'10.0.0.12'
Communications link failure
The last packet sent successfully to the server was 0 milliseconds ago.
```

重点看：

- 是否识别为 `connection_failure`
- 报告是否区分账号权限、网络连通性和数据库服务状态
- 敏感字段是否被脱敏
- 质量评估是否能通过

讲法：

> 这个 case 展示的是日志证据可能包含多个方向，比如权限和网络。LogMind 会先做脱敏，再基于故障类型检索相关知识，最后让模型结合证据给出分层排查建议。

### Case 3：JVM OOM

```text
Exception in thread "http-nio-8080-exec-10" java.lang.OutOfMemoryError: Java heap space
at com.example.order.OrderService.queryOrders(OrderService.java:87)
```

重点看：

- 是否识别为 `resource_exhaustion`
- 是否提取 `OutOfMemoryError` 和 `Java heap space`
- 修复建议是否包含堆内存、对象增长、慢查询或缓存等排查方向

讲法：

> 这个 case 说明 LogMind 不只是识别错误类型，还会把关键证据解析到结构化字段里，方便后续做历史查询和统计复盘。

## 面试现场演示顺序

1. 先打开 README，讲项目定位。

   讲法：

   > LogMind 是一个面向日志排障的 Agent，不是通用聊天机器人。它的目标是把一次日志诊断做成可追踪、可评估、可沉淀的流程。

2. 在前端输入端口冲突日志。

   重点展示：

   - 结构化诊断报告
   - 故障类型
   - 严重等级
   - 关键证据
   - 修复建议

3. 打开最近诊断。

   重点展示：

   - 完整报告
   - 参考知识
   - 相似历史案例
   - Agent trace
   - 质量评估

4. 打开诊断统计。

   重点展示：

   - 轨迹覆盖率
   - 知识命中率
   - 历史案例命中率
   - 平均质量分
   - 平均诊断耗时
   - 平均模型耗时

5. 运行 Eval 脚本。

   讲法：

   > 我没有只靠手动观察 demo，而是把常见故障整理成 eval case。每次调整 prompt、分类规则或知识库后，都可以跑评估看有没有退化。

## 面试官可能追问时的回答

更完整的追问清单见 `docs/logmind-interview-qna.md`。下面只放现场最常见的几类短回答。

### 这为什么不是玩具 Demo？

可以这样答：

> 如果只是一个聊天框接大模型，那确实很像玩具。LogMind 的区别在于它有完整诊断链路。输入先脱敏，再判断诊断意图，随后分类故障类型，检索知识库和历史案例，生成结构化报告，再做解析、保存、trace 和 eval。它关注的是 Agent 应用工程闭环，而不是单次模型回复。

### 现在最大短板是什么？

可以这样答：

> 当前最大短板是生产化还不完整。比如相似案例现在主要按 fault_type 召回，还不是 embedding 语义检索。token 成本统计也还没有完全接入供应商返回。我的定位是先把校招和初中级 AI 应用项目最重要的链路、评估和观测做完整，再逐步补生产治理。

### 为什么相似案例不直接放进知识库？

可以这样答：

> 我把两者分开了。知识库是静态 Runbook，适合放稳定的排障知识。相似案例是动态经验，来自 SQLite 中的历史诊断记录。这样系统运行越久，历史经验越多，同时不会污染静态知识库。

### 为什么要记录耗时？

可以这样答：

> Agent 项目不能只看回答质量，还要看响应速度。尤其多了 RAG、历史召回和 Eval 后，延迟会变成真实问题。所以我把总诊断耗时和模型生成耗时记录到 trace metadata，再在观测面板里聚合展示。

### 日志切片现在怎么做？

可以这样答：

> 当前版本主要面向用户粘贴关键日志或上传 `.log/.txt` 文件，文件会整体读取、脱敏后作为一次诊断输入。生产化时我会把日志切片单独做成模块，优先按时间窗口、trace_id、服务模块和异常堆栈聚合，避免长日志直接塞给模型。

### RAG 召回率怎么测？

可以这样答：

> 当前已经做了引用准确性和事实一致性评估，能防止模型引用不存在的知识。严格召回率下一步会给 eval case 加 `expected_knowledge_titles`，统计 top-k 是否命中预期 Runbook，比如 recall@1、recall@3。

### bad case 怎么迭代？

可以这样答：

> 我会先看 agent_trace 判断失败来源。如果是分类错，就补分类规则和 eval case；如果是检索没命中，就调整知识库、chunk 或 top-k；如果是模型生成问题，就改输出契约和 prompt；如果是事实不一致，就补 golden replay 和事实一致性测试。

## 看到什么程度可以进入前端收尾

你能不看文档讲清楚下面这段，就可以进入前端视觉和演示材料最终收尾：

> LogMind 是一个日志排障 Agent。它会先对日志脱敏，再判断是否是诊断请求。进入诊断后，系统用规则分类器识别故障类型，同时检索静态知识库和 SQLite 中的历史诊断案例。LLM 生成结构化报告后，系统会解析字段，保存诊断历史，记录 agent_trace，并计算质量分、引用准确性和事实一致性。前端不只展示回答，还展示参考知识、历史案例、质量评估和运行观测。
