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
- 登录：`kabi-boss-cli` / Cookie（`~/.config/boss-cli/credential.json`）
- 列表：`GET /wapi/zprelation/friend/getGeekFriendList.json?page=N`
- 最近消息：`GET /wapi/zpchat/geek/userLastMsg?friendIds=`（poll 后 enrich）
- 历史：`GET /wapi/zpchat/geek/historyMsg` + `maxMsgId` 分页
- 文本发送：**MQTT**（`mqtt_chat.py`，对齐 zhipin-geek）→ CLI → HTTP fallback
- 发简历：`exchange/request type=3` + `resumeId`（`resume_catalog.json`）
- 对话 Core：`POST /api/internal/reply`
- 参考仓（本地不提交）：`boss-bridge/_ref/zhipin-geek/`

## 待开发

- [x] 拉取单会话历史 API（`historyMsg` + 分页；C3 仍可再稳）
- [x] Geek 侧文本发送：MQTT 优先（zhipin-geek）；CLI/HTTP 兜底
- [x] 统一 HTTP：`boss_http.py`（`zp_token` / 抖动限流 / cookie 回写 / 37·9·121）
- [x] poll：`enrich_last_messages`（userLastMsg）再判 `_needs_reply`
- [x] Boss 话术：少追问岗位、主动推简历；禁「知识库/不想猜测」元话术
- [x] `lastMessageInfo.fromId` vs `friend.uid`：区分自己发的消息，避免回自己
- [x] **已发简历启发式**：扫 `historyMsg`（`对方已查看了您的附件简历` / `aid=38` / `encryptResumeId`）→ `meta.resumeAlreadySent`，避免重复推简历
- [x] **本地 `resumeSent*`**：`SessionStore` 持久化；热路径本地优先，历史命中 bootstrap 回写；真发入口默认 OFF（`BOSS_ENABLE_SEND_RESUME`）
- [ ] 未读-only 模式配置 `REPLY_UNREAD_ONLY=true`（可选收紧）
- [ ] 速率：单轮 `--limit`，全局每日上限
- [ ] 审计日志：谁问了啥、回了啥（本地文件，不上传）

### 发简历真链路 + 本地会话状态（P1）

当前 dry-run 只产出 `actions: [{type:"send_resume"}]`；是否已发过：本地标记优先，否则扫历史并 bootstrap。

- [x] **探测 / 封装发简历入口（对齐 zhipin-geek）**
  - `BossTransport.find_pending_resume_request`：解析 HR「我想要一份您的附件简历」卡片（agree deep-link `aid=38`）
  - `BossTransport.send_resume`：`POST /wapi/zpchat/exchange/request`（`type=3`）+ 同意卡 `acceptItemContact`；`securityId` 优先 `getBossData`；请求头对齐仓库：`X-Requested-With` + `zp_token=bst`
  - **2026-08-31 实测**（谷女士@软通）：缺 `zp_token` 时 `121`；补齐后 **`code=0`**。首次误发英文默认件；已按 JD 选附件：
    - 后端中文 `简历-田麟-6年经验-后端AI方向` / 数据中文 `简历-田麟-6年-数据开发+ai` / 英文仅明确要时发 `resume-lin-tian-backend-ai-en`
    - 目录：`boss-bridge/resume_catalog.json`；选轨：`resume_select.py`（`jobName`+对方文案；外企≠英文简历）
  - 单次脚本：`python scripts/send_resume_once.py --session-id … [--dry-run] [--force]`
  - `BOSS_ENABLE_SEND_RESUME=false`（默认）：C1 dry-run 只记 intent；C2 `[RESUME-SKIP]`
  - 单测：`python -m unittest tests.test_resume_markers tests.test_resume_select tests.test_mqtt_encode`
- [ ] **C2 批量真发**（单会话已通；开闸前注意风控，曾有 `code=36`）
  - 主动发 / 被动同意路径已接线；文本走 MQTT
- [x] **对齐 zhipin-geek 的传输层优化（2026-08-31）**
  - `boss_http.py`：统一客户端
  - `mqtt_chat.py`：文本 MQTT
  - `historyMsg` 分页 + `userLastMsg` enrich
  - 参考源码：`_ref/zhipin-geek/`（gitignore）
- [x] **发送成功写本地标识**（`SessionStore` / `data/sessions.json`）
  - 字段：`resumeSentAt`、`resumeTrack`、`resumeSource`（`history_bootstrap` | `proactive` | `agree_request`）
  - 热路径：`resumeSentAt` 已有 → 直接 `resumeAlreadySent=true`，**跳过** `historyMsg` 扫描
  - 冷启动 / 无标记：仍用现有历史启发式 bootstrap 一次，成功后回写本地
  - **注意**：请求文案「我想要一份您的附件简历」已从「已发」标记中拆出（`RESUME_REQUEST_MARKERS`）
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
