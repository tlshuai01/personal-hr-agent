# 架构：Chat Core 与 Channel 分离

## 问题

Boss 直聘对接、猎聘对接、网页分享链接对话——表面都是「和 HR 聊天」，但：

- **能力内核相同**：检索知识库 → 约束生成 → 防幻觉 → 敏感拦截
- **接入形态不同**：Cookie / 非官方 API / Web SSE / 消息格式 / 轮询 vs 推送

若把 Boss 逻辑写进 Next.js 路由或 `src/lib/boss*.ts`，Core 会被渠道细节污染，第二个渠道（猎聘）会复制粘贴 RAG 逻辑。

## 推荐模型

```
                    ┌─────────────────────────────────┐
                    │     personal-hr-agent (Core)     │
                    │  knowledge · RAG · reply · policy │
                    │  /api/chat (share)               │
                    │  /api/internal/reply (channel)   │
                    └───────────────┬─────────────────┘
                                    │ HTTP + shared secret
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
      boss-bridge            liepin-bridge          web-guest
      (Python 守护)          (未来)                  (浏览器 SSE)
```

### Core 负责

1. **唯一事实源**：`knowledge/` 入库与版本
2. **RAG 检索**与上下文组装
3. **LLM 调用**与 system prompt / 拒答策略
4. **对外契约**：
   - Guest：`POST /api/chat`（share token）
   - Channel：`POST /api/internal/reply`（`x-bridge-secret`）
5. **可选**：Owner 管理、评测、审计

### Channel 负责

1. 平台登录态（Cookie / OAuth / CLI）
2. 会话列表、未读、消息拉取
3. 消息 → Core 标准 `messages[]` 格式
4. Core 返回 `reply` → 平台发送（或 dry-run 日志）
5. **渠道侧**去重、轮询频率、平台 ToS 风险自担

Core **不知道** Boss 的 `friendId`、`getGeekFriendList.json`；Channel **不知道** ES / 向量细节。

## 拆仓库还是模块？

| 方案 | 适用 | 说明 |
|------|------|------|
| **A. 本仓子目录**（当前） | 1 个渠道、快速试行 | `boss-bridge/` 已足够；边界靠文档 + 禁止 Core import 渠道代码 |
| **B. monorepo `channels/`** | 2+ 渠道并行 | Core npm 包 + 多个 channel 包，共享 OpenAPI |
| **C. 独立 Git 仓库** | 渠道实验频繁、ToS 隔离 | `tlshuai01/boss-bridge` 只调 Core URL；Core 发 semver |

**建议路径**：A（现在）→ 跑通 C1/C2 后，若加猎聘则 **C 或 B**。

## API 契约（Channel → Core）

已实现：`POST /api/internal/reply`

演进方向（预留，见 [`chat/API.md`](../chat/API.md)）：

```typescript
// 统一 Channel 请求
{
  channel: "boss" | "liepin" | "manual",
  sessionId: string,
  messages: { role: "user" | "assistant", content: string }[],
  meta?: { bossName?, company?, jobTitle?, ... }
}

// 统一响应
{
  ok: true,
  reply: string,
  blocked: boolean,
  blockReason?: string,
  sources: string[]
}
```

## 反模式（禁止）

- ❌ 在 `src/lib/rag.ts` 里调用 Boss HTTP
- ❌ 在 `boss-bridge` 里复制粘贴 prompt / 检索代码
- ❌ 把 share token 逻辑与 Boss session 混用同一存储
- ❌ 在 Core 里写「仅 Boss 可用」的分支（应通过 `channel` 字段扩展 meta）

## 待决事项

- [ ] OpenAPI / JSON Schema 发布为 `docs/roadmap/chat/openapi.yaml`
- [ ] Channel 健康检查：`GET /api/internal/health`（可选）
- [ ] 多渠道并发时的 rate limit 与配额（Core 侧）
