# 大模型与 Agent 开发工程师：项目面试问答

> 适用场景：大模型开发工程师、Agent 开发工程师、AI 应用平台工程师、智能运维 / 智能治理相关岗位。  
> **统一最新口径**：当前请优先按两个项目来讲：
>
> 1. `..\..\gdsagent\docs\aiagent\GDS_Governance_AI_Agent_项目详解.md`
> 2. `..\..\gdsagent\docs\aiagent\GDS_Ops_AI_Agent_项目详解.md`
>
> 本文档基于当前 `gdsagent-python-rebuild` 的真实实现整理，覆盖两个项目：
>
> 1. **治理 / 数据 Agent 项目**
> 2. **运维 / Oncall Agent 项目**

---

## Q1：请你先整体介绍一下这两个项目。

**回答思路：先讲业务问题，再讲技术方案，再讲拆分边界。**

**示范回答：**

我目前把这套 Agent 能力拆成了两个相对独立的项目方向。

第一个是 **治理 / 数据 Agent 项目**，主要解决数据治理和 onboarding 场景的问题，比如：

1. 用户用自然语言生成数据契约
2. 基于 Kafka topic 生成 governance contract proposal
3. 分析只读 SQL 的血缘关系
4. 回答 MDM / LDM / Hive / onboarding 相关问题

第二个是 **运维 / Oncall Agent 项目**，主要解决生产告警处理的问题，比如：

1. 接收 PagerDuty 或通用告警
2. 路由到结构化 Playbook 场景
3. 汇总 metrics、logs、SOP、历史案例和只读运维证据
4. 输出适合手机端和 ChatOps 的结构化运维卡片

从技术上看，这两个项目都不是简单的 prompt 封装，而是：

1. 用 FastAPI 暴露服务边界
2. 用 LangGraph 编排多步骤 Agent 流程
3. 用共享 LLM 工厂统一调用模型能力
4. 用工具层做结构化 grounding
5. 用 Redis 做记忆持久化
6. 用 hybrid 文档检索补充非结构化知识
7. 用轻量知识图谱补充概念关系知识

我之所以把它们拆成两个项目来讲，是因为它们在真实生产中服务对象、依赖系统、发布节奏和权限边界都不一样：

1. 治理 Agent 面向数据开发、治理平台用户
```

**来源**：原 `大模型与Agent开发工程师_项目面试问答.md`  
**迁移至**：raw/eval/大模型与Agent开发工程师_项目面试问答.md