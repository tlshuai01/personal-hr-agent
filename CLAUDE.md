# CLAUDE.md — personal-hr-agent

## 项目定位

构建**个人 Agent 能力**的独立产品仓库。

**一阶段目标**：候选人维护个人知识库，生成限时分享链接；HR 打开链接即可与「数字化候选人」文本对话，准确回答经历 / 项目 / 技术问题。

规格真源：[`docs/PERSONAL_HR_AGENT_SPEC.md`](docs/PERSONAL_HR_AGENT_SPEC.md)  
产品说明：[`docs/README.md`](docs/README.md)

实现细节与规格冲突时，**以 SPEC「必须实现」条款为准**。

---

## 一阶段 MVP 范围

必须有：

1. 流式文本对话（SSE / chunked）
2. 本地 Markdown 知识库 + RAG
3. 防幻觉：无依据则明确拒答
4. 限时分享链接（过期、可选消息上限、可作废）
5. Owner 管理页（密码保护）
6. 黄金集评测（检索覆盖；可选 LLM 端到端）

明确不做（一阶段）：语音/TTS、多租户 SaaS、独立向量库、跨会话长期记忆、自动解析 PDF/Word。

---

## 技术选型（锁定）

| 层 | 选型 |
|----|------|
| 框架 | Next.js 15 App Router + TypeScript + React 19 |
| LLM | `openai` npm，兼容 Ollama / DeepSeek 等 |
| 校验 | zod |
| 持久化 MVP | JSON 文件（`data/`） |
| 向量 | 无独立向量库；`data/index.json` 进程内检索 |
| 脚本 | tsx（index / eval / smoke） |

约束：

- API route：`export const runtime = "nodejs"`（需要 `fs`）
- 部署需要可写持久盘挂载 `data/`（不适合无盘 Serverless）

---

## Agent 工作约定

- **有文件改动及时 commit + push**（用户要求；勿积压未提交变更）
- **密钥永不进 Git / remote**：仅 `.env.local`、`boss-bridge/.env`；详见 [`docs/roadmap/security/SECRETS.md`](docs/roadmap/security/SECRETS.md)
- **个人知识库仅本地**：`C:\Users\tl_94\PycharmProjects\personal-knowledge`（含电话/邮箱），**禁止** `git add` / push；仓库内 `knowledge/` 已弃用，见 [`knowledge/MOVED.md`](knowledge/MOVED.md)
- 先读 SPEC，再改代码；新增能力先更新 SPEC「必须/不做」再实现。
- `knowledge/` 是唯一事实源；回答必须可追溯到检索片段，禁止编造经历。
- 分享链接视为临时凭证：默认短过期、可设消息上限；勿把真实 `.env` / 敏感知识库提交公开仓库。
- 知识库中的容量 / QPS / 成本等数字是用户**个人估算**，可入库、可对外讲；不要擅自当涉密删改，相关改动先征询用户。
- 评测门槛：检索黄金集覆盖目标 ≥90%（`npm run eval:retrieval`）；有 LLM 再跑 `npm run eval`。
- 本项目与 `gds-ai-experience` 分离：那边是过往项目理解文档，不要把企业 GDS 规格直接拷进本仓实现，除非明确要「借鉴思路」并改写成个人场景。

---

## 建议目录（实现时对齐 SPEC）

```text
personal-hr-agent/
  CLAUDE.md
  docs/
    README.md
    PERSONAL_HR_AGENT_SPEC.md
  knowledge/           # 个人 Markdown 事实源
  evals/golden.jsonl
  scripts/
  src/app/             # 页面 + API
  src/lib/             # RAG / LLM / share / storage
  data/                # 运行时（gitignore）
```

当前阶段以文档与规格为主；落地代码时按 SPEC §3 目录结构补齐。

---

## 常用命令（实现后）

```bash
npm install
npm run knowledge:index
npm run dev
npm run smoke
npm run eval:retrieval
npm run eval          # 需配置 LLM
```
