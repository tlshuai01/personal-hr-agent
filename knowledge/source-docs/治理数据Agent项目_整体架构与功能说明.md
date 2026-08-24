# 治理数据 Agent 项目：整体架构与功能说明

> **统一口径对齐**：本文件应与 `..\..\gdsagent\docs\aiagent\GDS_Governance_AI_Agent_项目详解.md` 保持一致。  
> 当前统一的项目讲法是 **GDS Governance AI Agent**，而不是继续把治理能力拆成很多互相独立的小项目。

## 1. 项目定位

该项目对应当前仓库中的 **治理 / 数据服务域**，本地入口为：

- `governance_main.py`

它的目标不是做一个泛化聊天机器人，而是围绕 **数据治理 onboarding、元数据理解、SQL 血缘分析** 提供一个统一的治理主入口，面向数据开发、治理平台和 MDM 使用者。

但从当前项目演进方向看，治理域更合理的长期形态不是继续并列堆叠多个小 Agent，而是逐步收敛为：

1. **Governance Copilot** 作为统一主入口
2. onboarding / review / knowledge / lineage 作为内部 capability

从服务边界上看，这一项目可以被表述为：

> 一个面向 GDS / MDM 治理场景的多能力 Agent 服务，以 Governance Copilot 作为统一主入口，内部统一承载 contract 生成、governance contract assist、SQL lineage 和 MDM 助手问答。

关于 `ESP Processor`、`DEC`、原始 CJS 流程的关系，以及为什么治理 Agent 应按场景而不是按零散功能重构，参见：

- `ai-doc/ESP_DEC数据流作用分析与治理Agent重规划建议.md`

---

## 2. 业务背景

在真实生产中，治理域常见痛点包括：

1. topic / 表 onboarding 依赖人工梳理，效率低
2. LDM / MDM / Hive / Wiki 信息分散，查询成本高
3. SQL 血缘分析依赖人工阅读，难以快速解释
4. 用户只想得到"结构化结果"，不希望自己搭建 LLM runtime

因此当前项目当前阶段把最有价值的能力收敛为后端服务：

1. **Governance Copilot**：治理域统一主入口
2. **Contract Agent**：面向表级 onboarding 的子能力
3. **Governance Contract Agent**：面向 Kafka topic -> governance contract proposal 的子能力
4. **SQL Lineage Agent**：面向只读 SELECT SQL 的辅助分析子能力
5. **MDM Assistant**：面向治理知识问答与多轮解释的子能力与兼容入口
6. **Agent Runner**：用统一 SSE 协议对外暴露 agent 执行过程

不过从真实使用场景看，更合理的收敛方向是：

1. 以 `Governance Copilot` 作为统一入口
2. 把 `Contract Agent` 和 `Governance Contract Agent` 并入统一治理主入口
3. 把 `MDM Assistant` 定位为知识问答子能力
4. 把 `SQL Lineage Agent` 从独立主入口降级为 planning/review 场景下的辅助工具

---

## 3. 整体架构

```text
Client / UI
  -> FastAPI Governance Service
      -> Agent Runner / REST API Layer
      -> LangGraph Agents / Service Orchestration
      -> Shared Tool Registry
      -> Shared LLM Factory
      -> Redis Session Memory（在线多轮）
      -> 可选 Kafka chat audit topic（append-only，下游 Flink / 湖仓）
      -> Hybrid Document RAG + Domain Graph
      -> Mock / Real Metadata Sources
```

### 3.1 API 层

治理服务当前暴露的核心接口包括：

1. `POST /contract/onboard`
2. `POST /governance/contract-assist`
3. `POST /governance-copilot/chat`
4. `POST /sql-lineage/analyze`
5. `POST /mdm-assistant/chat`
6. `POST /support-agent/chat`
7. `POST /agent/execute`

其中：

- REST 接口适合后端集成和页面表单调用
- `agent/execute` 适合 SSE 流式活动回放和统一运行时承载

### 3.2 Agent / Service 层

核心能力分工如下：

| 能力 | 入口 | 主要作用 |
|------|------|----------|
| Governance Copilot | `/governance-copilot/chat` | 治理侧统一主入口与 capability routing |
| Contract Agent | `/contract/onboard` | 表级契约生成（兼容入口 / 子能力） |
| Governance Contract Agent | `/governance/contract-assist` | topic -> governance contract proposal（兼容入口 / 子能力） |
| SQL Lineage Agent | `/sql-lineage/analyze` | 只读 SELECT 血缘分析（辅助子能力） |
| Support Agent | `/support-agent/chat` | 对外 support 问答，必要时桥接 ops 只读诊断 |
| MDM Assistant | `/mdm-assistant/chat` | 内部治理知识助手 / 兼容旧入口 / governance knowledge path |
| Agent Runner | `/agent/execute` | 统一 SSE 协议、轻量活动追踪 |

### 3.3 共享基础层

治理域当前复用了一组共享组件：

1. **LLM Factory**
   - 统一接入共享 LLM 能力
   - 用户无需自部署模型
2. **Tool Registry**
   - Hive 表结构
   - Wiki 查询
   - LDM / Governance LDM 检索
   - hybrid 文档检索
3. **Shared Query Understanding**
   - 在进入共享知识层前先做 metadata extraction、rewrite、expansion 和 path shaping
4. **Redis Session Memory**
   - 用于 MDM Assistant、Support Agent 多轮聊天连续性（以及兼容路径）
   - 会话读路径不经过 Kafka
5. **可选 Kafka 聊天审计**
   - 在消息成功 `append_message` 后异步写入 topic（`CHAT_AUDIT_KAFKA_*`），与 Redis 解耦，供离线分析；详见 `ai-doc/functions/Chat_Message_Kafka_审计流.md`
6. **Hybrid Document RAG**
   - 通过 Elasticsearch dense + BM25 hybrid 检索补充 SOP / onboarding / 治理文档类知识
7. **Knowledge Ingestion Framework**
   - 支持 upload / Confluence source
   - 支持 raw / parsed markdown 映射
   - 让治理知识不再只依赖仓库内 docs
8. **Lightweight Domain Knowledge Graph**
   - 对 `CJS / ESP / ESS / DEC / Contract / Signal / LDM / Dataset` 这类高频概念关系做结构化补充

---

## 4. 核心功能拆解

## 4.1 Governance Copilot

**目标**：作为治理域统一主入口，先判断用户问题类型，再复用已有治理能力完成请求。

当前内部支持：

1. `onboarding_contract`
2. `governance_contract`
3. `mapping_review`
4. `knowledge`
5. `sql_lineage`

当前主流程：

```text
receive governance request
  -> analyze capability
  -> delegate to existing governance capability
  -> normalize response
```

---

## 4.2 Contract Agent

**目标**：把"上线一张表"的自然语言描述转换为结构化 contract。

当前主流程：

```text
extract_table_name
  -> get_table_details
  -> search_ldm
  -> generate_contract
```

关键特点：

1. 先结构化提取表名，再补元数据，不是直接裸 prompt
2. Hive / Wiki / LDM 工具参与上下文增强
3. LDM 匹配失败不阻塞主流程
4. 最终返回结构化 contract JSON

## 4.3 Governance Contract Agent

**目标**：面向 Kafka topic，生成 governance-style contract proposal。

当前实现吸收了 `gds-governance` POC 中最有价值的部分：

1. topic name 提取
2. governance LDM 候选检索
3. 结构化 governance contract JSON 生成
4. SSE 事件协议输出

这里的关键取舍是：

> 不要求用户自己部署 LLM，也不把复杂前端绑定逻辑一起迁进来，而是把核心能力沉淀为统一后端服务。

## 4.4 SQL Lineage Agent

**目标**：对只读 SELECT SQL 做来源表、JOIN、过滤、聚合的结构化分析。

当前主流程：

```text
parse_sql
  -> get_source_details
  -> generate_lineage
```

关键特点：

1. 明确只支持 SELECT，拒绝写操作
2. 通过正则提取源表，先把只读血缘场景做清晰
3. 调用 Hive 元数据工具补上下文
4. 返回结构化 `lineage` JSON

## 4.5 Support Agent / MDM Knowledge Layer

**目标**：对外回答 "表 / 主键 / LDM / MDM / onboarding / 问题状态" 类问题，并在遇到运维症状时调用 ops 只读诊断能力。

当前链路：

```text
receive chat request
  -> shared chat triage
  -> load session history
  -> governance knowledge path
  -> optional ops diagnose bridge
  -> call shared LLM
  -> persist chat history
```

能力边界清晰分工如下：

1. **Support 对外解释**：客户可读的状态、原因、影响说明
2. **结构化 grounding**：Hive / Wiki / LDM / governance tools
3. **运维状态桥接**：`/ops-agent/diagnose` 或对应 service 能力
4. **文档知识补充**：hybrid document RAG
5. **概念关系补充**：lightweight domain knowledge graph
6. **知识接入补充**：upload / Confluence 入库后的文档可直接复用同一套共享检索

## 4.6 Agent Runner

**目标**：提供统一 SSE 执行协议，便于前端或平台侧观察 agent 执行过程。

当前事件类型包括：

1. `connected`
2. `agent_activity`
3. `business_data`
4. `answer`
5. `complete`
6. `error`

这让治理类 Agent 不只是"返回最终答案"，还能把：

1. 工具调用
2. 中间状态
3. 结构化业务数据

显式暴露给调用方。

---

## 5. 当前功能价值

从简历和项目叙事角度，这个项目的价值主要体现在：

1. **把治理类复杂操作服务化**
   - 用户不用自己组装 LLM + 工具 + 记忆
2. **把结构化元数据工具和非结构化文档检索组合起来**
   - 不是纯聊天，也不是纯表查询
3. **把多种治理能力统一到一个服务边界**
   - Governance Copilot 成为主入口，contract、lineage、MDM 助手、SSE runner 不再各自为战
4. **保留生产可演进性**
   - 当前已用真实向量检索打通文档知识链路，后续重点转向真实元数据源接入

---

## 6. 当前实现边界

当前版本仍然是 **production-shaped MVP**，主要边界包括：

1. 部分元数据工具仍以 mock 数据为主
2. 文档知识库当前已升级为 Elasticsearch hybrid retrieval，并新增了 upload / Confluence ingestion MVP，但 registry 仍是轻量实现
3. SQL lineage 仍以正则解析为主，字段级血缘未完全覆盖
4. Governance Contract Agent 还未接提交 / 发布动作
5. Agent Runner 当前只正式承载 governance contract 场景

---

## 7. 推荐讲法

如果在简历或面试里介绍，推荐这样描述：

> 我把治理域能力收敛成一个 Governance Copilot 主入口，统一承载表 onboarding、topic 合同生成、mapping/review、SQL 血缘分析和 MDM 助手问答；底层通过共享 LLM、结构化元数据工具、Redis 会话记忆、hybrid 文档检索和轻量知识图谱来增强回答质量，并通过 SSE runner 对外暴露结构化执行过程。

---

## 8. 相关入口与文档

### 服务入口

- `governance_main.py`

### 相关文档

1. `ai-doc/notes/03_服务拆分与本地运行说明.md`
2. `ai-doc/Contract_Agent_功能与流程.md`
3. `ai-doc/Governance_Contract_Agent_功能与流程.md`
4. `ai-doc/SqlLineage_Agent_功能与流程.md`
5. `ai-doc/MDM_Assistant_功能与流程.md`

---

**更新时间**：2026-04-23
**来源**：原 `治理数据Agent项目_整体架构与功能说明.md`
**迁移至**：raw/architectures/治理数据Agent项目_整体架构与功能说明.md