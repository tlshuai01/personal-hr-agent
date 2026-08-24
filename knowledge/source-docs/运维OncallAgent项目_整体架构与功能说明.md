# 运维 Oncall Agent 项目：整体架构与功能说明

> **统一口径对齐**：本文件应与 `..\..\gdsagent\docs\aiagent\GDS_Ops_AI_Agent_项目详解.md` 保持一致。  
> 当前统一的项目讲法是 **GDS Ops AI Agent**，而不是只把它讲成单点的 HubGptAgent 告警分析能力。

## 1. 项目定位

该项目对应当前仓库中的 **运维 / 告警服务域**，本地入口为：

- `ops_main.py`

它的目标是把原本依赖人工阅读 Playbook、切换多套监控系统和拼接沟通信息的 oncall 过程，收敛成一个 **playbook-driven oncall copilot**。

从服务边界上看，这个项目可以被表述为：

> 一个面向 GDS / CJS 生产告警的运维 Agent 服务，负责接收 webhook 告警、匹配 Playbook 场景、汇总只读证据、调用共享 LLM 做诊断，并输出适合手机端 / IM / ChatOps 消费的结构化运维卡片。

---

## 2. 业务背景

真实 oncall 处理往往面临以下问题：

1. 告警类型多，标题格式不统一
2. 指标、日志、SOP、历史案例分散在不同系统
3. 值班同学需要在手机端快速看结论，不适合阅读原始 JSON / Grafana 数据
4. 即使知道告警原因，也不一定清楚该通知谁、怎么通知、哪些动作能做

因此当前项目采用的核心思路是：

1. 先把 SOP / Playbook 结构化
2. 再按场景做 router 和 evidence orchestration
3. 最后把结果压缩成统一的 `uiCard`

---

## 3. 整体架构

```text
PagerDuty / Generic Alert Source
  -> FastAPI Ops Service
      -> HubGptAgent (LangGraph)
          -> parse alert
          -> route to playbook
          -> infer systemKind + toolPlan
          -> collect required read-only evidence
          -> bounded controlled ReAct (optional tools)
      -> lookup SOP / retrieve memory
      -> call shared LLM
      -> build uiCard
      -> persist alert memory
      -> Redis Alert Memory
      -> Hybrid SOP / Doc Retrieval
      -> Ops Chat Memory / Feedback Store
      -> Mock / Real Ops Tool Integrations
```

### 3.1 API 层

当前运维服务暴露的接口包括：

1. `POST /webhook/pagerduty`
2. `POST /webhook/alert`
3. `POST /ops-agent/chat`
4. `POST /ops-agent/diagnose`
5. `POST /ops-agent/feedback`
6. `GET /webhook/health`
7. `GET /ops-agent/health`

它的输入可以来自：

1. PagerDuty webhook
2. 通用监控告警系统
3. 后续 ChatOps / bot / mobile app 转发层

### 3.2 核心 Agent 层

运维域当前的核心是 `HubGptAgent`。

它已经不是简单的"告警摘要器"，而是一个显式工作流：

```text
webhook alert
  -> identify alert type
  -> route to playbook scenario
  -> infer systemKind and resolve toolPlan
  -> gather required readonly evidence
  -> bounded optional ReAct supplementation
  -> diagnose with hybrid knowledge
  -> validate conclusion with rule gate and tool-less agent review
  -> repair once if needed
  -> build structured response card
  -> save to alert memory
```

---

**来源**：原 `运维OncallAgent项目_整体架构与功能说明.md`  
**迁移至**：raw/architectures/运维OncallAgent项目_整体架构与功能说明.md