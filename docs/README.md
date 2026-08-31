# 个人 HR 对话 Agent

可分享、带过期令牌的网页对话 Agent：基于你的 `knowledge/` 知识库 + RAG，准确回答经历 / 项目 / 技术问题。

> **完整架构/复现规格（给其他 Coding Agent）：** [`PERSONAL_HR_AGENT_SPEC.md`](PERSONAL_HR_AGENT_SPEC.md)  
> **当前架构图（Mermaid + 模块说明）：** [`PROJECT_ARCHITECTURE.md`](PROJECT_ARCHITECTURE.md)  
> **项目约定：** [`../CLAUDE.md`](../CLAUDE.md)

## 功能

- HR 通过限时链接 `/c/<token>` 打开即可聊（无需注册）
- Owner 在 `/admin` 创建 / 作废链接（密码保护）
- 流式文本回答 + 防幻觉策略（无依据则明确说没有记录）
- 本地知识索引与黄金集评测

## 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 配置环境变量

```bash
copy .env.example .env.local
```

关键项：

| 变量 | 说明 |
|------|------|
| `OWNER_PASSWORD` | 管理台密码 |
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | OpenAI 兼容对话模型 |
| `APP_URL` | 分享链接域名（本地默认 `http://localhost:3000`） |

**本地开发（Ollama，零费用）：**

```bash
# 安装并启动 Ollama 后
ollama pull qwen2.5
```

`.env.local`：

```
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=qwen2.5
```

**生产推荐（DeepSeek）：**

```
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=sk-你的密钥
LLM_MODEL=deepseek-chat
```

Embedding 可留空：默认使用本地词袋向量，无需额外 API。检索评测不达标再配置 `EMBEDDING_*`。

密钥策略：见 [`roadmap/security/SECRETS.md`](roadmap/security/SECRETS.md)

### 3. 填写知识库并建索引

仓库内已有**演示候选人「李明」**数据，可直接跑通。替换为你自己的内容后执行：

```bash
npm run knowledge:index
```

### 4. 启动

```bash
npm run dev
```

- 首页：http://localhost:3000
- 管理台：http://localhost:3000/admin
- 健康检查：http://localhost:3000/api/health

在管理台创建限时链接，把 URL 发给 HR。

## 评测

```bash
# 不依赖 LLM：索引 + 检索 + 分享链接生命周期
npm run smoke

# 不依赖 LLM：黄金集检索覆盖率（目标 ≥90%）
npm run eval:retrieval

# 依赖 LLM：端到端生成质量（需 Ollama 或 DeepSeek）
npm run eval
```

黄金集：`evals/golden.jsonl`（30 题）。报告输出到 `data/eval-report.json`。

## 目录结构

```
knowledge/           # 唯一事实源（请替换演示数据）
evals/golden.jsonl   # 评测题
scripts/             # 索引 / 评测 / smoke
src/app/             # Next.js 页面与 API
src/lib/             # RAG / LLM / 分享链接 / 存储
data/                # 运行时索引与 JSON 存储（gitignore）
```

## 部署建议

本 MVP 使用本地 JSON 文件持久化分享链接与对话日志，适合：

- 一台带磁盘的 Node 主机（推荐）：`npm run build && npm start`
- Docker / 国内云主机 / Railway / Fly.io（挂载持久卷到 `data/`）

不建议直接用无持久磁盘的 Serverless（如默认 Vercel）存放 `data/`，除非改为外部数据库。

### Docker

```bash
docker build -t my-agent .
docker run --rm -p 3000:3000 \
  -e OWNER_PASSWORD=change-me \
  -e LLM_BASE_URL=https://api.deepseek.com/v1 \
  -e LLM_API_KEY=sk-... \
  -e LLM_MODEL=deepseek-chat \
  -e APP_URL=https://your-domain.example \
  -v my-agent-data:/app/data \
  my-agent
```

### 生产检查清单

1. 替换 `knowledge/` 为真实材料并 `npm run knowledge:index`
2. 配置 DeepSeek（或其它）API Key
3. 设置强 `OWNER_PASSWORD` 与正确 `APP_URL`
4. `npm run smoke` 通过；无 Key 时可先 `npm run eval:retrieval`；有 Key 再跑 `npm run eval`
5. 自测：创建链接 → 对话 → 过期/作废

### 验收记录（本地已完成）

- `npm run smoke`：索引 + 混合检索 + 分享链接生命周期通过
- `npm run eval:retrieval`：黄金集检索覆盖 ≥90%
- `npm run build` + `npm start`：健康检查、创建/校验/作废分享链接、聊天页可打开
- 完整 LLM 对话评测：需配置 Ollama 或 DeepSeek 后执行 `npm run eval`

- 分享链接等同于临时访问凭证，请设短过期与消息上限
- 勿将 `.env.local`、真实敏感知识库提交到公开仓库
- 页面页脚已提示：关键录用以真人沟通为准
