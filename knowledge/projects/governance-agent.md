# 项目：数据治理 AI Agent

## 背景

服务数据开发 / 治理 / Support，把契约、血缘、主数据问答与协作能力做成 Agent 产品。

## 我的角色

治理域 Agent 流程设计与实现理解：Copilot 统一入口、Contract、SQL Lineage、MDM、Support 协作。

## 技术栈

LangGraph / LangChain、FastAPI、统一 `/chat` 路由、消费知识平台检索能力。

## 我做了什么

- Governance Copilot：治理统一入口
- Contract Agent：表级契约生成（LangGraph）
- Governance Contract：topic → contract proposal
- SqlLineage Agent：**仅允许 SELECT**，写操作拒绝（非简单套开源库）
- MDM Assistant：治理知识问答
- Support ↔ 协作场景的双聊天设计

## 难点与决策

- 权限与发布边界：治理进程与知识入库主链路分离
- 血缘安全：强制 SELECT-only
- 与 Support / Ops 协作时 Persona 与工具边界清晰

## 可追问点

- LangGraph 状态怎么设计
- 契约提案如何人工确认
- 为什么 SqlLineage 要自己控安全性

## 不确定就别说

- 内部系统真实库名、未脱敏 topic、客户数据样例
