# Chat API 设计

## 设计原则

**所有对外「说话」的能力都走 Chat Runtime**，区别只是认证与传输：

| 入口 | 认证 | 传输 | 状态 |
|------|------|------|------|
| Guest 分享页 | `share token` | SSE / chunked | ✅ `/api/chat` |
| Boss Channel | `x-bridge-secret` | JSON 同步 | ✅ `/api/internal/reply` |
| 未来：猎聘 | 同上或独立 secret | JSON | 预留 |
| 未来：OpenAPI 第三方 | API Key | JSON / SSE | 预留 |

共享实现：`src/lib/reply.ts` → `generateReply(messages)`

## Guest API

```
POST /api/chat
Body: { token, messages[] }
Response: text stream + X-Retrieved-Sources
Errors: 403 share 失效；422 敏感拦截
```

## Internal Channel API

```
POST /api/internal/reply
Header: x-bridge-secret
Body: {
  channel: "boss",
  sessionId: string,
  messages: { role, content }[],
  meta?: { bossName, company, jobTitle }
}
Response: { ok, reply, blocked, blockReason, sources }
```

## 演进：统一 v1（预留）

```
POST /api/v1/chat
Authorization: Bearer <api-key> | x-bridge-secret | share-token-scheme
Body: {
  mode: "guest" | "channel",
  channel?: string,
  sessionId?: string,
  token?: string,
  messages: ...
}
```

- [ ] 版本化路径，旧路由保留 6 个月
- [ ] OpenAPI 3.1 描述
- [ ] rate limit：按 api-key / channel

## 错误码约定（预留）

| HTTP | code | 含义 |
|------|------|------|
| 401 | unauthorized | secret/token 无效 |
| 403 | share_expired | 分享链接失效 |
| 422 | blocked | 敏感策略拦截 |
| 502 | llm_error | 上游模型失败 |

## Smoke

```bash
npm run smoke          # guest + 索引
npm run smoke:bridge   # internal reply
```

## 待实现

- [ ] `GET /api/internal/health` — Channel 探活
- [ ] 结构化日志：sessionId、channel、sources（不含 full reply 到第三方日志）
