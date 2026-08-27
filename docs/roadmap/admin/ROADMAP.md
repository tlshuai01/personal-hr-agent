# 管理台路线图

## 已有

- `/admin` 密码保护
- 创建 / 作废 share link
- 过期与消息上限

## 待增

- [ ] 渠道状态面板（Boss bridge 是否在线 — 心跳 optional）
- [ ] dry-run 日志查看（读本地文件，不上云）
- [ ] 知识库「最后索引时间」与一键 reindex
- [ ] 敏感词策略编辑（当前硬编码在 `reply.ts` / `policies.py`）
- [ ] 导出对话审计（CSV，脱敏）

## 不做（一阶段）

- 多租户 SaaS 管理
- 在线编辑 Markdown（仍用 git + 本地文件）
