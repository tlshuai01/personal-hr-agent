# 猎聘渠道（占位）

> **未开始**。架构对齐 Boss Channel，仅替换 Transport 层。

## 预设目标

- [ ] 调研：猎聘 Web 聊天 API / Cookie 方案（无官方 Bot API 假设）
- [ ] `liepin-bridge/` 目录或独立仓库
- [ ] 复用 Core `POST /api/internal/reply`，`channel: "liepin"`
- [ ] 独立 secret：`LIEPIN_BRIDGE_SECRET`（可选）

## 与 Boss 共用

- SessionStore 模式
- policies 敏感词
- dry-run → auto-send 分阶段

## 差异点（待调研）

- 登录与 Cookie 字段
- 好友列表 / 未读字段名
- 发送消息 endpoint
- 反爬策略

## 前置条件

- Boss C1 dry-run 稳定
- Core Chat API 契约冻结（见 [`../chat/API.md`](../chat/API.md)）
