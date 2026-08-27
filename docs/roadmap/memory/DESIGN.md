# 记忆系统设计（预留）

## 范围界定

| 类型 | 一阶段 | 二阶段 | 存储位置 |
|------|--------|--------|----------|
| **知识记忆** | ✅ RAG 静态知识库 | 增量更新 | `knowledge/` + index |
| **会话短期记忆** | ⚠️ Channel 侧 JSON 去重 | Core 可选 | `boss-bridge/data/sessions.json` |
| **跨会话长期记忆** | ❌ 不做 | 可选 | TBD |
| **Share 对话日志** | ✅ 按 token 存 | 审计导出 | `data/app.json` |

SPEC 一阶段明确：**不做跨会话长期记忆**（避免 HR 侧误以为 Agent「记得上次聊过」）。

## 短期记忆（Session）

### Channel 层（当前）

- `SessionStore`：dedupe key、`messages[]` 最近 40 条
- 用途：多轮 C3、避免同一条 lastMsg 重复回复

### Core 层（预留）

```typescript
// 可选 header / body
sessionId: string
messages: ChatTurn[]  // Channel 维护或 Core 拉历史
```

Core **无状态**优先：Channel 传全量 `messages`，Core 不查 Boss 历史。

若 Core 要存 session：

- [ ] `data/sessions/<sessionId>.json`（按 channel 分区）
- [ ] TTL 7 天自动清理
- [ ] 不含 PII 明文导出选项

## 长期记忆（未来，谨慎）

仅在用户明确开启时：

- [ ] 「HR 问过的问题」写入 `knowledge/faq-learned.md` 需 Owner 审核后入库
- [ ] 禁止自动把 Boss 聊天写入知识库（防污染 / 隐私）

## 与 RAG 的边界

- **记忆** = 对话上下文与可选摘要
- **RAG** = 可引用的稳定事实
- 不得用 LLM 摘要替代 RAG 出处

## 待决

- [ ] C3 是否在 Core 提供 `GET /api/internal/session/:id`（一般不需要）
- [ ] 摘要压缩：messages >20 条时 sliding window vs LLM summary
