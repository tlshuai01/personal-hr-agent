# 本地个人知识库 — 迁移与 Git 策略

## 新位置（唯一真源）

```
C:\Users\tl_94\PycharmProjects\personal-knowledge\
```

## 为什么迁出仓库

- 含**姓名、电话、邮箱**与职业细节
- 用户要求：**知识库文档永远不要传到 remote**

## 本目录（personal-hr-agent/knowledge/）

- 已弃用，仅保留本说明
- 实际内容请编辑 `../personal-knowledge/`（或 `.env.local` 中的 `KNOWLEDGE_DIR`）

## 配置

`.env.local`：

```env
KNOWLEDGE_DIR=C:\Users\tl_94\PycharmProjects\personal-knowledge
```

## 索引

```bash
npm run knowledge:index
```
