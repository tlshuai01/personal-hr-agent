# personal-hr-agent

**官方产品名：个人求职 Agent**（Personal Job Agent）

个人求职场景的对话 Agent（**独立 Git 仓库**）：本地知识库 RAG + 限时分享链接 + 可选 Boss 渠道 Bridge。

> 仓库路径：`C:\Users\tl_94\PycharmProjects\personal-hr-agent`（与 `myAIProjects` 平级，请单独打开此目录）  
> 仓库/包名仍为 `personal-hr-agent`；对外口述与产品 UI 使用「个人求职 Agent」。

- 项目约定：[`CLAUDE.md`](CLAUDE.md)
- 实现规格：[`docs/PERSONAL_HR_AGENT_SPEC.md`](docs/PERSONAL_HR_AGENT_SPEC.md)
- 产品说明：[`docs/README.md`](docs/README.md)
- **待开发 / 路线图**：[`docs/roadmap/README.md`](docs/roadmap/README.md)

## Git / GitHub

本地仓库已初始化（`main` 分支，首次提交已完成）。

远程（已配置）：

```bash
git remote -v
# origin  git@github.com:tlshuai01/personal-hr-agent.git
```

**首次推送前**，在 GitHub 创建空仓库（不要勾选 README）：

https://github.com/new → 名称 `personal-hr-agent` → Create repository

然后：

```bash
git push -u origin main
```

账号主页：https://github.com/tlshuai01

## 快速开始

```bash
npm install
copy .env.example .env.local
npm run knowledge:index
npm run dev
```

管理台：`http://localhost:3000/admin`  
Boss 渠道：见 [`boss-bridge/README.md`](boss-bridge/README.md)
