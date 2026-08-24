# personal-hr-agent

个人 Agent 能力项目（**独立 Git 仓库**）。一阶段：与 HR 自动对话。

> 仓库路径：`C:\Users\tl_94\PycharmProjects\personal-hr-agent`（与 `myAIProjects` 平级，请单独打开此目录）

- 项目约定：[`CLAUDE.md`](CLAUDE.md)
- 实现规格：[`docs/PERSONAL_HR_AGENT_SPEC.md`](docs/PERSONAL_HR_AGENT_SPEC.md)
- 产品说明：[`docs/README.md`](docs/README.md)

## Git

```bash
git init   # 已完成
git status
```

如需推送到 Cursor / GitHub 远程，在本目录配置 `origin` 后 `git push -u origin main`。

## 快速开始

```bash
npm install
copy .env.example .env.local
npm run knowledge:index
npm run smoke
npm run eval:retrieval
npm run dev
```

- 首页：http://localhost:3000
- 管理台：http://localhost:3000/admin（密码见 `OWNER_PASSWORD`）
- 健康检查：http://localhost:3000/api/health

## 本机还缺什么？

| 能力 | 是否必须 | 现状建议 |
|------|----------|----------|
| Node.js 18+ / npm | **必须** | 已具备即可开发 |
| **LLM API**（对话） | **聊天必须** | 未装 Ollama 时：用 DeepSeek / 其它 OpenAI 兼容 API；或安装 [Ollama](https://ollama.com) 后 `ollama pull qwen2.5` |
| **Embedding API** | **可选** | 默认本地词袋向量，**可不配**；要更好检索再配 `EMBEDDING_*` |
| Docker | 可选 | 本机已有，可用于部署或跑 Ollama 容器 |

无 LLM 时仍可：`knowledge:index` / `smoke` / `eval:retrieval` / 管理台建链接；**真正对话**需要配置 `LLM_*`。
