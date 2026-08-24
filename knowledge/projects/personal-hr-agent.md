# 项目：个人 HR 对话 Agent

## 背景

构建个人 Agent 能力的一阶段产品：让 HR 通过限时链接与「数字化候选人」文本对话，准确回答经历 / 项目 / 技术问题。

## 我的角色

独立 Owner：规格、实现、知识库、评测与部署约束一体负责。

## 技术栈

Next.js 15 App Router、TypeScript、React 19、OpenAI 兼容 LLM SDK、zod、tsx 脚本；MVP 用 JSON 文件存分享链接与日志；默认本地词袋 Embedding，可选 API Embedding。

## 我做了什么

- 流式聊天 API + Chat UI
- Markdown 知识库切块 / 索引 / 混合检索（语义 + 关键词）
- 防幻觉 system prompt + boundaries 优先
- Owner 管理台：创建 / 作废限时分享链接
- smoke / 检索评测 / 可选 LLM 端到端评测
- 将过往项目理解文档提炼进 knowledge/ 作为事实源

## 难点与决策

- 不用独立向量库：个人知识体量足够，优先交付产品形态
- 分享链接=临时凭证：过期 + 消息上限 + 可撤销
- 无依据必须拒答，准确性优先于「听起来会说」

## MVP 明确不做

语音克隆、多租户 SaaS、跨会话长期记忆回放、自动解析 PDF/Word。

## 可追问点

- 本地 embedding 与 API embedding 如何切换
- 如何保证 HR 链路过期后不可聊
- 黄金集如何定义幻觉题
