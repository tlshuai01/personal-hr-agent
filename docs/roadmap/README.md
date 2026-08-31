# 待开发功能总览

> 个人求职 Agent 产品路线图与分类文档索引。  
> 规格真源仍见 [`PERSONAL_HR_AGENT_SPEC.md`](../PERSONAL_HR_AGENT_SPEC.md)；本文为**演进规划**，与已实现代码可并存。

更新：2026-09-01

---

## 架构原则（先读）

**Chat 是核心能力；Boss / 猎聘等是「渠道适配器（Channel）」，不是产品本体。**

| 层 | 职责 | 当前位置 |
|----|------|----------|
| **L1 Chat Core** | 对话运行时、RAG、记忆策略、对内 API | `personal-hr-agent`（本仓） |
| **L2 Knowledge** | Markdown 事实源、索引、评测 | `knowledge/` + `scripts/` |
| **L3 Channel** | 各平台消息拉取/发送、格式转换 | `boss-bridge/`（建议逐步独立或 `channels/`） |
| **L4 Schedule（规划）** | 面试预约日程；后续供 Agent 读写 | 见 [`schedule/INTERVIEW_CALENDAR.md`](./schedule/INTERVIEW_CALENDAR.md) |

详细论证：[`ARCHITECTURE.md`](./ARCHITECTURE.md)

---

## 分类文档

| 分类 | 文档 | 状态 |
|------|------|------|
| 架构 | [ARCHITECTURE.md](./ARCHITECTURE.md) | 已定方向，待落地拆分 |
| **当前架构图** | [../PROJECT_ARCHITECTURE.md](../PROJECT_ARCHITECTURE.md) | **已实现快照 + Mermaid** |
| RAG | [rag/DESIGN.md](./rag/DESIGN.md) | 一阶段已实现；二阶段待增强 |
| 记忆 | [memory/DESIGN.md](./memory/DESIGN.md) | 预留 |
| Chat API | [chat/API.md](./chat/API.md) | 部分实现；待统一契约 |
| **按岗位 Persona** | [chat/PERSONA_BY_ROLE.md](./chat/PERSONA_BY_ROLE.md) | **待实现** |
| **面试日程** | [schedule/INTERVIEW_CALENDAR.md](./schedule/INTERVIEW_CALENDAR.md) | **待做 · S0 独立小应用** |
| **Boss 搜岗打招呼** | [channels/BOSS_GREET.md](./channels/BOSS_GREET.md) | **G0 dry-run 已接线** |
| 渠道 · Boss | [channels/BOSS.md](./channels/BOSS.md) | C0 完成，C1 进行中 |
| 渠道 · 猎聘 | [channels/LIEPIN.md](./channels/LIEPIN.md) | 占位 |
| 渠道总览 | [channels/README.md](./channels/README.md) | — |
| 安全与密钥 | [security/SECRETS.md](./security/SECRETS.md) | **强制** |
| **知识库分类** | [knowledge/TAXONOMY.md](./knowledge/TAXONOMY.md) | 规划；**真源在本地 `personal-knowledge/`** |
| 评测 | [eval/ROADMAP.md](./eval/ROADMAP.md) | 预留 |
| 管理台 | [admin/ROADMAP.md](./admin/ROADMAP.md) | 预留 |

---

## 优先级建议（P0 → P2）

### P0 — 当前迭代（Boss 试行）

- [x] C0：Boss Cookie + 会话列表
- [x] C1 Core：`smoke:bridge` + DeepSeek；薪资/到岗可自动答；微信仍 blocked
- [x] C1 Boss：`boss-login.py --c1` / `main.py --phase c1 --once --limit 3`
- [x] 检索评测 ≥90%（`eval:retrieval` 96.2%）
- [x] 渠道与 Core 边界文档化（`PROJECT_ARCHITECTURE.md`）
- [x] 一键验收：`npm run p0:check`（需 dev 运行中）

### P1 — Chat Core 稳固

- [ ] **主动搜职位 + 打招呼（G0→G1）** → [`channels/BOSS_GREET.md`](./channels/BOSS_GREET.md)
- [ ] **按岗位 Persona + 知识库检索偏好**（后端轨 / 数据轨）→ [`chat/PERSONA_BY_ROLE.md`](./chat/PERSONA_BY_ROLE.md)
- [ ] 统一 Chat API 契约（guest share + internal channel）
- [ ] RAG：检索质量 / hybrid / rerank 可选增强
- [ ] 敏感话题策略可配置化
- [ ] Channel 注册表（配置驱动，非硬编码 boss）

### P2 — 扩展

- [ ] **面试日程小应用（S0）→ Agent 接入（S1）** → [`schedule/INTERVIEW_CALENDAR.md`](./schedule/INTERVIEW_CALENDAR.md)
- [ ] 会话级短期记忆（Channel 侧 + Core 可选持久）
- [ ] 猎聘 / 其它渠道适配器（独立包）
- [ ] Embedding API 可选接入（提升检索，非必须）
- [ ] 管理台：渠道开关、dry-run 开关、审计日志

---

## 仓库策略建议

**现阶段**：本仓 monorepo，`boss-bridge/` 作为子目录即可。  
**下一阶段**：若 Boss 与猎聘并行开发，建议：

```
personal-hr-agent/     # Chat Core + Knowledge + Web
channels/
  boss-bridge/         # 或独立 git 仓库，只依赖 Core HTTP API
  liepin-bridge/       # 占位
```

独立仓库的好处：渠道代码与 ToS 风险隔离、发布节奏独立；Core 保持稳定 semver API。

---

## 相关链接

- 试行进展：[`../boss-bridge/PROGRESS.md`](../../boss-bridge/PROGRESS.md)
- 项目约定：[`../CLAUDE.md`](../../CLAUDE.md)
