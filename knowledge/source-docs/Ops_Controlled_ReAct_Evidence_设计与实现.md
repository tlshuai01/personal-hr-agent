# Ops Controlled ReAct Evidence 设计与实现

> 对标得物 Troubleshooter 文章中的 ReAct 排查循环，但保留 Playbook 驱动的稳定性边界。

## 1. 设计目标

Ops Agent 需要同时满足两类诉求：

1. **稳定性**：高频 oncall 场景必须按 Playbook 固定顺序收集证据，避免 LLM 自由发挥。
2. **灵活性**：当 required 证据不足时，允许 LLM 在**白名单 optional 工具**中补充 1~2 步。

因此当前实现采用 **Playbook-first + Controlled ReAct** 混合模式，而不是纯 ReAct。

## 2. 总体流程

```text
webhook alert
  -> parse_alert
  -> route playbook scenario
  -> infer systemKind (flink_realtime / api_service / batch)
  -> resolve toolPlan.required
  -> collect required read-only tools (async)
  -> controlled_react (optional tools, max N steps)
  -> lookup_sop + retrieve_memory
  -> analyze_alert
  -> validate_conclusion
  -> repair_conclusion (at most 1 retry)
  -> build_response_card
```

对应代码：

- `src/agents/hubgpt_agent/graph.py`
- `src/agents/hubgpt_agent/evidence_planner.py`
- `src/agents/hubgpt_agent/conclusion_validator.py`
- `src/agents/hubgpt_agent/llm_conclusion_validator.py`
- `src/agents/hubgpt_agent/playbook_scenarios.json`

## 3. systemKind 与 toolPlan

### 3.1 systemKind

| systemKind | 典型场景 | 默认 required 工具 |
|---|---|---|
| `flink_realtime` | consumer lag / checkpoint / Flink 实时链路 | `query_flink_job_logs`, `query_kafka_lag_metrics`, `query_flink_runtime_metrics` |
| `api_service` | API 错误率 / RT / 服务不可用 | `query_app_logs` |
| `batch` | UC4 / HDFS / Spark / DLS 批处理 | 由 `evidence_sources` 映射到 UC4/HDFS/Spark/DLS 工具 |

Playbook 场景可在 `playbook_scenarios.json` 中显式覆盖：

```json
{
  "systemKind": "flink_realtime",
  "toolPlan": {
    "required": ["query_flink_job_logs", "query_kafka_lag_metrics"],
    "optional": ["get_flink_job_status"]
  }
}
```

### 3.2 为什么不是纯 ReAct

纯 ReAct 在生产 oncall 中有三个风险：

1. 工具选择不稳定，同类告警可能走不同路径。
2. 可能调用不在白名单内的写操作工具。
3. 排查过程难以审计和回放。

当前方案把 **required 工具** 固定为 Playbook 契约，只把 **optional 工具** 交给 bounded ReAct。

## 4. Controlled ReAct 边界

配置项（见 `env.project-3-ops.example`）：

```bash
OPS_TOOL_TIMEOUT_SECONDS=8
OPS_CONTROLLED_REACT_ENABLED=true
OPS_CONTROLLED_REACT_MAX_STEPS=2
```

执行规则：

1. 只允许调用当前 Playbook `toolPlan.optional` 中的工具。
2. 工具名必须在 systemKind 白名单内。
3. 每步最多选 1 个工具；总步数不超过 `OPS_CONTROLLED_REACT_MAX_STEPS`。
4. 工具超时/失败只降级，不中断整条诊断链路。
5. 若 LLM planner 不可用，走 deterministic fallback（例如 API 场景从日志 traceId 自动补 `query_call_log`）。

## 5. 工具契约（mock，可替换真实客户端）

### 5.1 Flink / 实时链路

| 工具 | 作用 |
|---|---|
| `query_flink_job_logs` | JM/TM error/warn 日志 |
| `query_kafka_lag_metrics` | consumer lag / partition hotspot / upstream lag |
| `query_flink_runtime_metrics` | job/TM/pod CPU、内存、GC、backpressure |
| `get_flink_job_status` | 现有 job health 摘要 |

### 5.2 API 服务

| 工具 | 作用 |
|---|---|
| `query_app_logs` | 应用错误日志 + traceId 提取 |
| `query_call_log` | CAL/AppMon 调用链分析：沿 parent/downstream rlogid 受限展开、异常聚合与瓶颈定位 |
| `query_app_metrics` | QPS / RT / errorRate / CPU / memory / GC |

防护：`query_app_logs` 拒绝 `endpoint="/"`，避免无意义全量查询。
`query_call_log` 接受 `traceId` 或可信 AppMon URL，并使用 upstream hop、downstream depth、
总 fetch 数、去重和 Tool timeout 限制查询范围。详见
`ai-doc/functions/Ops_CAL_Call_Chain_Analysis.md`。

### 5.3 Batch

沿用现有 UC4 / HDFS / Spark / DLS mock 工具，由 batch systemKind 自动映射。

## 6. 结论 Validation 门禁（规则 + Agent 两层）

分析完成后、出卡前增加两层验收：

```bash
OPS_CONCLUSION_VALIDATION_ENABLED=true
OPS_CONCLUSION_VALIDATION_MAX_RETRIES=1
OPS_LLM_CONCLUSION_VALIDATION_ENABLED=true
OPS_LLM_CONCLUSION_VALIDATION_TIMEOUT_SECONDS=12
```

### 6.1 第一层：规则验收（必须有）

规则检查包括：

1. 是否有明确 root cause
2. 是否至少有 1 条成功只读证据
3. 结论是否与证据弱关联（grounding）
4. 是否错误宣称自动执行 `manual_only` / `confirm_required` 动作
5. 证据失败率过高时是否过度自信

### 6.2 第二层：Validation Agent（规则通过后才运行）

`llm_conclusion_validator.py` 是一个**无工具**的独立审查 Agent，只基于已收集证据检查：

1. 根因是否被证据语义支撑
2. 建议是否可执行且不越权
3. 不确定性是否与证据质量匹配

Agent 不可用时不阻断主链路，规则层仍作为最终门禁。

失败后最多修复 1 轮：

- `supplement`：再补 1 个 optional 只读工具后重分析
- `rewrite`：注入 validation feedback 后重写结论
- 仍失败 → 降级出卡：`confidence=low`、`needsReview=true`

uiCard 新增字段：

- `validation.passed`
- `validation.ruleValidation`
- `validation.agentValidation`
- `validation.issues`
- `confidence`
- `needsReview`

## 7. 状态与可观测性

HubGptAgent state 新增：

- `system_kind`
- `tool_plan`
- `react_steps`
- `validation_result`
- `validation_retry_count`
- `conclusion_confidence`
- `needs_review`

`readonly_tool_results` 中每条证据包含：

- `tool`
- `phase` (`required` / `react` / `validation_repair`)
- `status` (`ok` / `timeout` / `failed`)
- `summary`
- `data`

## 8. 当前边界

### 已实现

1. systemKind 推断与 toolPlan 解析
2. required 工具并发收集
3. bounded optional ReAct（白名单 + 步数上限 + 超时降级）
4. Flink/API/Batch 三类工具契约（mock），其中 CAL Tool 已实现完整上下游遍历算法和 provider 边界
5. Playbook 场景显式 toolPlan 配置
6. 单元测试与 HubGptAgent 工作流测试
7. 结论 Validation 门禁：规则层 + 无工具 Validation Agent + 一次 bounded repair

### 未实现

1. 真实 Prometheus / APM / 日志平台客户端（CAL Tool 当前仍需 Sherlock/AppMon 生产 provider）
2. 排查过程文件系统审计
3. 自动通知编排（Slack / Teams 生产回发）

## 9. 推荐讲法

> 我们的 Ops Agent 不是纯 ReAct，而是 Playbook 驱动的主链路加上受控 ReAct 补证，并在出卡前做两层 Validation：先规则门禁，再让无工具 Validation Agent 做语义审查；如果结论不合格，最多再修复 1 轮，否则降级出卡并标记人工复核。
