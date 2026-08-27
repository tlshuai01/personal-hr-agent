# 渠道适配器总览

每个 **Channel** 是一个独立进程（或独立仓库），通过 Core 的 Internal API 消费对话能力。

## 已实现

| Channel | 目录 | 文档 |
|---------|------|------|
| Web Guest | Next.js `/api/chat` | [`../chat/API.md`](../chat/API.md) |
| Boss 直聘 | `boss-bridge/` | [BOSS.md](./BOSS.md) |

## 占位

| Channel | 文档 | 说明 |
|---------|------|------|
| 猎聘 | [LIEPIN.md](./LIEPIN.md) | 未开始 |
| 拉勾 | — | 按需 |
| 手动/Webhook | — | 通用 ingress |

## Channel 最小接口（每个适配器实现）

```python
class ChannelAdapter:
    def list_sessions(self) -> list[Session]: ...
    def fetch_messages(self, session_id) -> list[Message]: ...
    def send_message(self, session_id, text) -> None: ...  # C2+
    def to_core_payload(self, session, messages) -> dict: ...
```

Core 侧不变。

## 配置

每个 Channel 自有 `.env`：

- `AGENT_BASE_URL`
- `BOSS_BRIDGE_SECRET` / `LIEPIN_BRIDGE_SECRET`（可与 Core 分 secret）
- 平台 Cookie / CLI 路径

## 发布策略

- Core：稳定，semver tag
- Channel：可 `0.x` 快速迭代，Breaking 不影响 Guest 页
