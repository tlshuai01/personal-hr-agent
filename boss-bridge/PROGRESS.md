# Boss Bridge 试行进展

> 本地进度记录（个人试用，非官方 API）

## 当前状态

| 阶段 | 状态 | 说明 |
|------|------|------|
| **C0** | **已通过** | Cookie 登录 OK；沟通列表可拉取（约 300 会话）；需 `page=1` |
| **C1 Core 链路** | **已通过** | `npm run smoke:bridge` + DeepSeek 生成 + 薪资 blocked |
| **C1 Boss dry-run** | **已通过** | 多轮报告见 `reports/`；简历已发本地化已落地 |
| **发简历真链路** | **已通 / 默认 OFF** | `resumeId` 选轨；`BOSS_ENABLE_SEND_RESUME`；谷女士实测中文后端 OK |
| **传输层** | **已对齐 zhipin-geek** | MQTT 文本、`boss_http` 限流、`historyMsg` 分页、`userLastMsg` |
| **C2** | 未开 | 自动发送，确认 C1 日志后再开 |
| **C3** | 未开 | 多轮历史（分页已具备） |

更新日期：2026-08-31

## P0 验收（Core，2026-08-27）

| 检查项 | 命令 | 结果 |
|--------|------|------|
| 知识索引 | `npm run knowledge:index` | ✅ 900 chunks（`personal-knowledge`） |
| 基础 smoke | `npm run smoke` | ✅ |
| Bridge + LLM | `npm run smoke:bridge` | ✅ DeepSeek 453 字回复 + 薪资 blocked |
| 检索评测 | `npm run eval:retrieval` | ✅ **96.2%**（25/26） |
| 一键 P0 | `npm run p0:check` | 需先 `npm run dev` |

## C0 结论

1. **登录**：`boss login --cookie-source chrome` 成功（含 `__zp_stoken__`、`zp_at`）。
2. **不要用 F12 抄 Cookie**：Boss 页面对 DevTools 有反调试；用 boss-cli 从浏览器抽 Cookie 或 `--qrcode`。
3. **列表坑**：`getGeekFriendList.json` **必须带 `page=1`**。上游 `boss chat` 不传 `page` 时返回空 `zpData`；bridge 已改为直接 HTTP 分页拉取。
4. **PATH**：Windows 上 `boss.exe` 可能不在 PATH；`boss-bridge/.env` 可写全路径：  
   `BOSS_CLI_BIN=C:/Users/.../Scripts/boss.exe`

## C1 dry-run（Boss 侧）

```bash
# 0. 浏览器保持 zhipin.com 已登录；Core 已 npm run dev

# 1. 刷新 CLI 凭证（封装脚本，默认从 Chrome 抽 Cookie，不先 logout）
cd boss-bridge
python scripts/boss-login.py --verify-only
python scripts/boss-login.py --c1          # 或 .\scripts\boss-login.ps1 -C1

# 2. 手动等价命令
boss login --cookie-source chrome          # 勿轻易 boss logout
.\.venv\Scripts\python main.py --phase c1 --once --limit 3
```

**2026-08-27 样例**：300 会话，启发式 286「需回复」；`--limit 3` 处理前 3 条，均为 `[DRY-RUN]`，DeepSeek 生成正常。

观察 `[DRY-RUN]` / `[BLOCKED]` / `[AGENT-BLOCKED]`，**不要**急着开 C2。

## 风险

- 违反平台 ToS 可能封号；接口随时变更。
- Cookie / `__zp_stoken__` 会过期，需 `boss logout && boss login` 刷新。
