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
- [x] Boss 话术：少追问岗位、主动推简历；禁「知识库/不想猜测」元话术
- [x] `lastMessageInfo.fromId` vs `friend.uid`：区分自己发的消息，避免回自己
- [x] **已发简历启发式**：扫 `historyMsg`（`对方已查看了您的附件简历` / `aid=38` / `encryptResumeId`）→ `meta.resumeAlreadySent`，避免重复推简历
- [x] **本地 `resumeSent*`**：`SessionStore` 持久化；热路径本地优先，历史命中 bootstrap 回写（真发 API 仍待接）
- [ ] 未读-only 模式配置 `REPLY_UNREAD_ONLY=true`（可选收紧）
- [ ] 速率：单轮 `--limit`，全局每日上限
- [ ] 审计日志：谁问了啥、回了啥（本地文件，不上传）

### 发简历真链路 + 本地会话状态（P1）

当前 dry-run 只产出 `actions: [{type:"send_resume"}]`；是否已发过：本地标记优先，否则扫历史并 bootstrap。

- [ ] **探测 / 封装发简历 API**（或 Chrome CDP 兜底）
  - 主动发：首轮兴趣 / 对方要简历时执行 `send_resume`
  - 被动同意：对方「请求附件简历」卡片 → 同意（`aid=38` 一类）后确认发送成功
- [x] **发送成功写本地标识**（`SessionStore` / `data/sessions.json`）— *历史 bootstrap 已落地；真发成功写 `proactive` 待 API*
  - 字段：`resumeSentAt`、`resumeTrack`、`resumeSource`（`history_bootstrap` | 预留 `proactive`）
  - 热路径：`resumeSentAt` 已有 → 直接 `resumeAlreadySent=true`，**跳过** `historyMsg` 扫描
  - 冷启动 / 无标记：仍用现有历史启发式 bootstrap 一次，成功后回写本地
- [x] **会话状态本地持久化（本切片）** — 详见 [`../memory/DESIGN.md`](../memory/DESIGN.md)
  - 必持久：`processed` 去重、`resumeSent*`、最近 N 条 messages
  - 建议持久：`jobTrack` / flags 字段已预留；摘要仍可选
  - 禁止：自动把 Boss 原文写入 `knowledge/`
- [ ] **开场白按职位选轨**（勿通用「Java 后端和 Agent / 数据平台」）— 详见 [`../chat/PERSONA_BY_ROLE.md`](../chat/PERSONA_BY_ROLE.md)
  - 优先用列表 `jobName`/`title` 推断；JD 详情接口仅职位名含糊时再拉
- [ ] **JD 薪资区间**（可选）：会话列表当前**通常无** `salaryDesc`；`encryptJobId` 详情接口待探测。有区间则写入 meta，对方谈薪时勿反问「能给多少」；无区间时若对方已说给不到期望，话术改为「薪资可灵活、看合适度」（已写入 prompt + `compensation.md`）

## 独立仓库迁移清单

- [ ] 抽离 `boss-bridge/` → `tlshuai01/boss-channel`
- [ ] README 只依赖 Core URL + secret
- [ ] CI：不对 Core 跑 Boss 集成测试
