# 项目：运维 Oncall AI Agent

## 背景

面向 SRE / Oncall，告警接入后给出可执行的诊断建议与结构化卡片，缩短排障路径。

## 我的角色

Ops Agent 架构与安全边界：Playbook-first、受控 ReAct + Evidence、uiCard、反馈闭环。

## 技术栈

FastAPI、HubGPT/OpenAI 兼容 LLM、Playbook / Runbook Schema、Webhook、受控工具调用。

## 我做了什么

- 告警 webhook 接入与 Ops 聊天入口
- Playbook 场景覆盖规划与 schema 设计
- Controlled ReAct + Evidence：先剧本后受控推理
- 结构化 uiCard 输出给协作界面
- 明确禁止自动执行修复（重启、扩容、改配置）

## 难点与决策

- 「自动化修复」诱惑 vs 生产安全 → 只建议不执行
- 风暴告警下的稳定性与降级
- 证据链（Evidence）让结论可审计

## 可追问点

- Playbook 与自由 ReAct 如何切换
- 安全分级怎么定义
- 与 Support 双聊天如何协同

## 不确定就别说

- 真实告警 payload、内部 runbook 机密步骤、未授权系统账号
