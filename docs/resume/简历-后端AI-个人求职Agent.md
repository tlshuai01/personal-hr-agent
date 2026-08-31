# 田麟

**Java / Python 后端 · 高并发系统 · Flink 实时计算 · RAG/Agent 平台 · 个人求职 Agent**

> 联系方式见 Boss 直聘 / 面试沟通（公开仓库版本不写手机与邮箱）

6年经验 · 英语工作语言 · 上海

---

## 求职意向

Java / Python 后端开发工程师（营销中台 / 活动引擎 / 高并发业务系统 / AI Agent & RAG 平台 / 分布式架构）

---

## 教育背景

| 学校 | 学历 | 专业 | 时间 |
|------|------|------|------|
| 东北大学 | 硕士 | 电子与通信工程 | 2020.06 |
| 沈阳建筑大学 | 本科 | 通信工程 | 2016.07 |

---

## 专业技能

- **常用语言**：Java、Python（均为日常主力）
- **语言与框架**：Java 8、Spring Boot、MyBatis、Dubbo；Python、FastAPI、LangGraph / LangChain；TypeScript、Next.js
- **数据库与缓存**：MySQL、Redis
- **消息与治理**：RabbitMQ、ZooKeeper、Sentinel、XXL-Job；Kafka
- **检索与 AI**：Elasticsearch hybrid、Embedding、RAG 多源入库；个人侧进程内混合检索（语义 + 关键词）
- **架构与方法**：DDD 分层、微服务；Agent 编排网关、SSE 流式对话；渠道 Bridge（轮询 + MQTT）
- **AI 辅助工程**：日常使用 Cursor / Copilot 做需求拆解、生成与 Review
- **运维与可观测**：Docker、Kubernetes、Prometheus、Grafana

---

## 工作经历

### 上海华钦信息科技有限公司（eBay）｜大数据开发工程师｜2024.11 – 至今

- 主导 **GDS** 企业知识问答平台（RAG 混合检索 + 对话运行时），服务 8k+ 内部用户、月活 3k+
- 设计并实现 **治理域 AI Agent** 与 **运维 Oncall AI Agent**（LangGraph / Playbook / uiCard）
- **CJS** Flink 链路运维优化及数据血缘追踪能力建设

### 慧博云通科技股份有限公司（爱立信中国）｜后端开发工程师｜2021.07 – 2024.09

- 运营商抽奖/活动执行平台策略域与抽奖主链路；中间件重构与性能优化；Prometheus 监控

### 中移（苏州）软件技术有限公司｜技术经理｜2020.07 – 2021.07

- 云业务运营平台技术管理与交付；Jenkins CI/CD

---

## 项目经验

### 个人求职 Agent（独立产品）｜进行中

**技术栈**：Next.js 15、TypeScript、OpenAI 兼容 LLM、zod；Python Bridge（httpx、MQTT、Cookie 登录）

面向求职场景的对话与渠道自动化产品：**本地 Markdown 知识库 RAG** + **限时分享链接** + **Boss 直聘渠道**。

- Chat Core：流式 SSE 对话、防幻觉拒答、Owner 管理台；对内 `internal/reply` 供渠道调用
- 知识工程：个人知识库分类维护、混合检索、黄金集评测（检索覆盖目标 ≥90%）
- Boss Bridge：沟通列表轮询、只回新消息 baseline、MQTT 文本发送、按 JD 选附件简历、发简历闸门与本地去重
- 搜岗打招呼：配置化关键词 / 城市 / **薪资下限** / **跳过词（实习、日结等）** / **活跃时段**；dry-run 审计与真发闸门分离
- 自动回复文末标注来源，便于招聘方识别 Agent 代发

### 营销能力平台｜爱立信｜2022.07 – 2024.04

**技术栈**：Spring Boot、MyBatis、MySQL、Redis、RabbitMQ、Dubbo、Sentinel

- DDD 策略域与抽奖主链路；Redis+MQ 最终一致；大促可用性 99.95%+；峰值 QPS 2k+

### 动态多激活系统（EDA）｜爱立信｜2021.07 – 2022.07

**技术栈**：Spring Boot、K8s、Kafka、Cassandra、Prometheus

- 中间件与查询优化；动态线程池；可观测告警

### 客户旅程信号平台（CJS）｜eBay｜2024.11 – 2025.07

**技术栈**：Flink、Kafka、Java、MDM

- 日 80 亿+ 事件链路运维；Lag 小时级→分钟级；JEXL 评估优化

### GDS 企业知识问答平台｜eBay｜2024.11 – 2025.06

**技术栈**：Python、FastAPI、Elasticsearch、MinIO、Redis

- 多源入库、父子分块、hybrid Top-3 ~78%；SSE 首 token P95 < 1.5s

### GDS 治理 & 运维 AI 智能体｜eBay｜2025.03 – 至今

**技术栈**：Python、FastAPI、LangGraph

- 契约/血缘 Agent；Oncall Playbook + uiCard；预审与排障提效

---

## 自我评价

- 高并发后端 + AI 平台工程双线经验；能独立交付 RAG/Agent 产品形态
- 个人求职 Agent 把「知识库 → 对话 → 渠道自动化」跑通，强调防幻觉与风控闸门
- 流处理稳定性与跨团队协作经验
