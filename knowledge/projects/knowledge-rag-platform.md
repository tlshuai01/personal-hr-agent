# 项目：企业知识问答平台（Hybrid RAG）

## 背景

面向研发 / 产品 / 数分的企业知识问答与检索平台，作为上层领域 Agent 的 L1 能力底座。

## 我的角色

参与/负责知识入库、混合检索、统一聊天运行时相关设计与实现梳理；能端到端讲清「入库 ↔ 在线」主链路。

## 技术栈

Python、FastAPI、Elasticsearch 8（dense_vector + BM25 + RRF）、MySQL 元数据、MinIO 文档 blob、Redis 会话、OpenAI 兼容 Embedding/LLM、SSE。

## 我做了什么

- 多源文档入库（含 Confluence 增量同步方向）与版本 / 影子发布思路
- Hybrid Retrieval：向量 + 关键词融合，再接 Rerank
- Query Understanding：改写 / 扩展 / 路径整形
- Unified Chat 入口：路由到不同 surface
- 流式输出、progress、references（引用）
- 评测与 helpful/wrong 反馈调优闭环

## 难点与决策

- 入库同步阻塞 → 事件化 / 异步作业 + 状态机
- 只用向量不够 → dense + BM25 + RRF
- 领域 Agent 不直连 ES → KnowledgeClient（in_process / http）保边界

## 可追问点

- Parent/Child chunking 为什么需要
- 零停机知识版本切换怎么做
- 检索与生成如何分别评测

## 可引用的规模口径

- 容量 / QPS / 成本等见知识库 `source-docs/00_三项目容量总览.md`（个人估算，可讲）
