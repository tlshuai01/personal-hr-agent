# Boss 直聘渠道

> 非官方 API，试用风险自负。进展：[`../../boss-bridge/PROGRESS.md`](../../boss-bridge/PROGRESS.md)

## 阶段

| 阶段 | 命令 | 状态 |
|------|------|------|
| C0 | `--phase c0` | ✅ 登录 + 列表（需 `page=1` HTTP） |
| C1 | `--phase c1 --once --limit 3` | 进行中 dry-run |
| C2 | `--phase c2` | 自动发送 |
| C3 | `--phase c3` | 多轮历史 |

## 技术栈

- Python：`boss-bridge/`
- 登录：`kabi-boss-cli` / Cookie
- 列表：`GET /wapi/zprelation/friend/getGeekFriendList.json?page=N`
- 对话 Core：`POST /api/internal/reply`

## 待开发

- [ ] 拉取单会话历史 API（C3 稳定）
- [ ] Geek 侧 send 接口实测与 fallback
- [ ] `lastMessageInfo.fromType` 完善「是否 HR 发来」
- [ ] 未读-only 模式配置 `REPLY_UNREAD_ONLY=true`
- [ ] 速率：单轮 `--limit`，全局每日上限
- [ ] 审计日志：谁问了啥、回了啥（本地文件，不上传）

## 独立仓库迁移清单

- [ ] 抽离 `boss-bridge/` → `tlshuai01/boss-channel`
- [ ] README 只依赖 Core URL + secret
- [ ] CI：不对 Core 跑 Boss 集成测试
