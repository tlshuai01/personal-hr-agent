# 安全与密钥策略

## 强制规则（Agent / 开发者必读）

1. **API Key、Cookie、Bridge Secret 仅允许存在于本地未跟踪文件**
   - `.env.local`
   - `boss-bridge/.env`
   - 系统凭据管理器
2. **禁止**将真实 Key 写入：
   - Git 跟踪文件（含 `*.md` 示例中的真实值）
   - 提交信息、Issue、截图
   - 推送到 GitHub / 任何 remote
3. **`.env.example` 只放占位符**（`change-me`、`sk-...`）
4. Agent 改代码时：若发现 Key 误入仓库，**立即 gitignore + 从索引移除**，并提醒用户轮换 Key
5. 对话中用户粘贴 Key：只写入 `.env.local`，回复里**不重复完整 Key**

## 本地文件

| 文件 | Git | 内容 |
|------|-----|------|
| `.env.local` | ❌ ignore | LLM / Embedding / BOSS_BRIDGE_SECRET |
| `boss-bridge/.env` | ❌ ignore | Bridge 配置 |
| `.env.example` | ✅ | 占位符模板 |

## Bridge Secret

- Guest share token ≠ Channel secret
- 生产环境 secret ≥ 32 随机字符
- 可按渠道分 secret（Boss / 猎聘）

## Boss Cookie

- 等同登录态，按密码级别保管
- 过期：`boss logout && boss login`

## 密钥轮换

若 Key 曾泄露或误提交：

1. 平台作废旧 Key
2. 更新 `.env.local`
3. `git log -p` 检查历史（必要时 `git filter-repo`，需用户确认）

## 检查清单（提交前）

```bash
git diff --staged | findstr /i "sk- api_key secret cookie"
# 不应出现真实密钥
```
