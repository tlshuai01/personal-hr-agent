# RAG 设计

## 现状（一阶段 MVP）

| 项 | 实现 |
|----|------|
| 事实源 | `knowledge/**/*.md` |
| 分块 | 按标题/段落（见 `scripts/index-knowledge.ts`） |
| 向量 | 默认 **本地 hash 词袋**（`data/index.json`，无独立向量库） |
| 检索 | 进程内余弦相似度，topK=8 |
| 生成 | LLM + system prompt + 检索上下文 |
| 防幻觉 | 无依据拒答；敏感词拦截（薪资/offer/联系方式） |

## 目标（二阶段增强）

### P1 — 质量

- [ ] **Hybrid 检索**：BM25（本地）+ 向量 RRF 融合（参考 gds-agent-local 思路，轻量落地）
- [ ] **Parent 回填**：命中 chunk 时扩展同文档段落
- [ ] **Query 改写**（可选 LLM）：口语问法 → 检索 query
- [ ] 检索分数阈值：低于阈值直接拒答

### P2 — Embedding

| 模式 | 何时用 |
|------|--------|
| **本地 hash**（默认） | 零成本、离线、隐私；黄金集 ≥90% 可接受 |
| **API Embedding** | 检索覆盖不足、同义词/跨语言多、知识库 >500 chunk |

可选配置（`.env.local`）：

```
EMBEDDING_BASE_URL=https://api.deepseek.com/v1   # 或其它 OpenAI 兼容
EMBEDDING_API_KEY=...
EMBEDDING_MODEL=...
```

**结论**：对话必须 LLM；**Embedding 非必须**，先用本地向量 + `eval:retrieval`，不达标再开 API。

### P3 — 运维

- [ ] 增量索引（git diff / mtime）
- [ ] 索引版本号写入 `data/index.json`，API 返回 `X-Index-Version`
- [ ] 多 collection（如 `projects/` vs `boundaries/` 加权）

## 数据流

```
用户问题
  → retrieve(query, topK)
  → formatRetrievedContext(chunks)
  → [system, context, ...messages]
  → LLM
  → reply + sources[]
```

## 与 Channel 的关系

RAG **只在 Core** 执行。Channel 只传 `messages` 最后一条 user 内容（或完整历史），不自己做检索。

## 评测

- `npm run eval:retrieval` — 不耗 LLM token
- `npm run eval` — 端到端，耗 LLM
- 黄金集：`evals/golden.jsonl`（扩展 Boss 高频 HR 问法）

## 待写规格

- [ ] chunk 策略参数表（size/overlap）
- [ ] hybrid 权重与 RRF k 默认值
- [ ] 拒答文案模板（中/英）
