# RAG 设计

## 现状（一阶段 MVP）

| 项 | 实现 |
|----|------|
| 事实源 | `KNOWLEDGE_DIR/**/*.md`（默认 `personal-knowledge/`） |
| 分块 | 按标题/段落（见 `src/lib/rag.ts`） |
| 向量 | 默认 **本地 hash 词袋**（`embeddingMode=local`）；可切 API Embedding |
| 检索 | 余弦 + 关键词加权；政策类 query 额外抬高 `01-基本信息` / `boss-channel` 等 |
| 生成 | LLM + **通用** system prompt + 检索上下文 |
| 口径分层 | **具体话术/数字只在知识库**；提示词不写 35W、开场模板等 |

## 提示词 vs 知识库

| 放提示词 | 放知识库（检索） |
|----------|------------------|
| 第一人称、防幻觉、禁元话术、IM 长短 | 薪资数字与谈不拢策略（`compensation.md`） |
| Boss：少追问、跟片段走、已发简历勿再推 | Boss 开场/推简历细则（`boss-channel.md`） |
| 会话态 meta（已发简历、职位名） | 到岗、外包、边界（`availability` / `leaving` / `boundaries`） |

## 目标（二阶段增强）

### P1 — 质量

- [ ] **Hybrid 检索**：BM25（本地）+ 向量 RRF 融合
- [ ] **Parent 回填**：命中 chunk 时扩展同文档段落
- [ ] **Query 改写**（可选 LLM）：口语问法 → 检索 query
- [ ] 检索分数阈值：低于阈值直接拒答

### P2 — 真向量 Embedding（推荐，当前匹配偏弱的主因）

现状默认是 **local hash**，不是语义向量；同义词（「预算」「包」「年薪」）召回差。

| 方案 | 说明 |
|------|------|
| **DeepSeek 同一把 key** | DeepSeek **目前无**公开 Embedding API，**不能**用 chat token 直接 embed |
| **OpenAI 兼容 Embedding** | 另配 `EMBEDDING_*`：OpenAI `text-embedding-3-small`、阿里云 DashScope、硅基流动、本地 Ollama `nomic-embed-text` 等 |
| **LLM 仍用 DeepSeek** | `LLM_*` 与 `EMBEDDING_*` **可分开**；改 embedding 后必须 `npm run knowledge:index` |

`.env.local` 示例（勿用 DeepSeek 当 embedding base）：

```
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=deepseek-chat

# 任选其一 OpenAI 兼容 embedding 服务
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small
# 或 Ollama：
# EMBEDDING_BASE_URL=http://127.0.0.1:11434/v1
# EMBEDDING_API_KEY=ollama
# EMBEDDING_MODEL=nomic-embed-text
```

切到 API 后 health 应显示 `"embeddingMode":"api"`。

### P3 — 运维

- [ ] 增量索引（git diff / mtime）
- [ ] 索引版本号写入 `data/index.json`，API 返回 `X-Index-Version`
- [ ] 多 collection（如 `projects/` vs `boundaries/` 加权）

## 数据流

```
用户问题
  → retrieve(query, topK)  (+ 政策 pin)
  → formatRetrievedContext(chunks)
  → [通用 system, context, 会话 meta, ...messages]
  → LLM
  → reply + sources[]
```

## 与 Channel 的关系

RAG **只在 Core** 执行。Channel 只传 `messages` + meta，不自己做检索。

## 评测

- `npm run eval:retrieval` — 不耗 LLM token
- `npm run eval` — 端到端，耗 LLM
- 黄金集：`evals/golden.jsonl`（扩展 Boss 高频 HR 问法，含「给不到 35W」）

## 待写规格

- [ ] chunk 策略参数表（size/overlap）
- [ ] hybrid 权重与 RRF k 默认值
- [ ] 拒答文案模板（中/英）
