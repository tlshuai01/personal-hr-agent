# Boss Bridge

Boss 直聘 ↔ `personal-hr-agent` 的分阶段桥接守护进程（非官方 API，**试用风险自负**）。

## 架构

```
Boss 直聘 (Cookie)  ←→  boss-bridge (Python)  ←→  POST /api/internal/reply
                              ↑
                    boss-cli 登录 + 直接 HTTP 拉列表（page=1+）
```

试行进度见 [`PROGRESS.md`](PROGRESS.md)。**C0 已通过**（沟通列表需 `page` 参数，勿依赖裸 `boss chat`）。

## 阶段说明

| 阶段 | 命令 | 行为 |
|------|------|------|
| **C0** | `--phase c0` | 验证登录 + 拉会话列表，一次性 |
| **C1** | `--phase c1`（默认） | 轮询未读 → Agent 生成回复 → **只打日志，不发 Boss** |
| **C1 试跑** | `--phase c1 --once --limit 3` | 单次轮询，最多处理 3 条未读（推荐先试） |
| **C2** | `--phase c2` | 非敏感题自动发送；敏感题 blocked |
| **C3** | `--phase c3` | 多轮：拉历史后再回复（C2 发送逻辑） |

敏感词（微信电话等）在 **bridge 侧** 与 **Agent 侧** 双重拦截；**薪资 / 到岗** 按知识库自动答。

## 前置条件

1. **personal-hr-agent** 已启动：`npm run dev`（默认 :3000）
2. `.env.local` 配置 `LLM_*` 与 `BOSS_BRIDGE_SECRET`
3. 安装 [boss-cli](https://github.com/jackwener/boss-cli)（PyPI: `kabi-boss-cli`）并完成登录：

```bash
pip install kabi-boss-cli
# 推荐：无二维码，从浏览器 Cookie 登录（任选一种）

# 方式 A — cmd（不受 PowerShell 执行策略限制，推荐）
scripts\boss-login-cookie.cmd
scripts\boss-login-cookie.cmd --browser edge

# 方式 B — 直接 Python
# %LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe scripts\boss-login-cookie.py

# 方式 C — PowerShell（若报「禁止运行脚本」，用 Bypass 或改用 cmd）
# powershell -ExecutionPolicy Bypass -File .\scripts\boss-login-cookie.ps1
```

## 安装与配置

```bash
cd boss-bridge
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env
```

`.env` 中 `BOSS_BRIDGE_SECRET` 必须与项目根 `.env.local` 一致。

## 运行

```bash
# C0：验证账号与会话列表
python main.py --phase c0

# C1：dry-run（推荐先试）
python main.py --phase c1

# C2：自动发送（确认 C1 日志无误后再开）
python main.py --phase c2

# C3：多轮上下文
python main.py --phase c3
```

## 内部 API

```http
POST /api/internal/reply
x-bridge-secret: <BOSS_BRIDGE_SECRET>
Content-Type: application/json

{
  "channel": "boss",
  "sessionId": "friend-123",
  "messages": [{ "role": "user", "content": "你好，介绍一下背景" }],
  "meta": { "bossName": "张HR", "company": "某公司", "jobTitle": "后端" }
}
```

## 风险说明

- 违反 Boss 直聘 ToS 可能导致封号
- 非官方接口随时可能变更；C2 发送走 CLI 或 Cookie HTTP 兜底，需实测
- 建议先用 **C1** 观察 1–2 天再开 C2

## 数据

- 会话去重与短记忆：`boss-bridge/data/sessions.json`（已 gitignore）
