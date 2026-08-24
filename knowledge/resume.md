# 经历摘要（个人理解口径）

## 项目一：企业知识问答平台（RAG + 对话运行时）

- 角色：核心开发 / 架构落地参与
- 内容：多源文档入库、版本与影子发布、ES dense + BM25 + RRF 混合检索、Query Understanding、统一 `/chat` 入口、SSE 流式、引用与进度事件
- 技术栈：Python、FastAPI、Elasticsearch、MySQL、Redis、MinIO、OpenAI 兼容 LLM

## 项目二：数据治理 AI Agent

- 角色：领域 Agent 设计与实现
- 内容：Governance Copilot、Contract Agent、SQL Lineage（仅 SELECT）、MDM 问答、Support 协作双聊天
- 技术栈：LangGraph / LangChain、统一聊天路由、知识平台 HTTP/in-process 消费

## 项目三：运维 Oncall AI Agent

- 角色：Ops Agent 流程与安全边界设计
- 内容：告警接入、Playbook 优先诊断、受控 ReAct + Evidence、结构化 uiCard、反馈闭环
- 硬约束：不自动执行重启/扩容/改配置，只给建议与安全分级

## 项目四：个人 HR 对话 Agent（进行中）

- 角色：独立产品 Owner
- 内容：限时分享链接、本地 Markdown 知识库 RAG、防幻觉拒答、Owner 管理台、黄金集评测
- 技术栈：Next.js 15、TypeScript、OpenAI 兼容 API、JSON 文件持久化、本地/API Embedding
