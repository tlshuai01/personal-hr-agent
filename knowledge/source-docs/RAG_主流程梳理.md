# RAG 主流程梳理

> 本文从全局视角说明项目中 RAG 的主流程，覆盖知识入库、索引发布、在线检索、回答生成和引用返回。当前实现口径为 **Elasticsearch Dense Vector + BM25 + RRF + 可选 BGE Rerank + Parent Chunk 回填 + 轻量知识图谱**。

## 1. 一句话概括

```text
多源文档
  -> 统一解析为 Markdown
  -> Parent/Child Chunking
  -> Embedding + Elasticsearch 混合索引
  -> Query Understanding
  -> Dense/BM25 双路召回
  -> RRF 融合 + 可选 Rerank
  -> Parent Chunk 回填 + 知识图谱补充
  -> LLM 基于证据生成回答
  -> SSE 返回进度、答案和引用
```

RAG 包含两条相互独立但最终衔接的链路：

1. **离线/准实时入库链路**：把原始文档加工成可检索的知识索引。
2. **在线问答链路**：理解用户问题、检索证据并生成带引用的回答。

---

## 2. 总体架构

```text
┌──────────────────────── 知识入库链路 ────────────────────────┐
│ Upload / Confluence                                         │
│   -> Registry + Ingestion Job                               │
│   -> MinIO Raw Blob                                         │
│   -> Parser -> Markdown                                     │
│   -> MinIO Parsed Blob                                      │
│   -> Heading/Block Chunking                                 │
│   -> Parent/Child Chunks                                    │
│   -> Embedding                                              │
│   -> Elasticsearch Child Chunk Index                       │
│   -> MySQL Parent Chunk + Version/Index Status              │
│   -> Publish/Switch Current Version                         │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────── 在线问答链路 ────────────────────────┐
│ User Query                                                  │
│   -> Unified Chat / Governance / Support / Ops              │
│   -> Intent Routing                                         │
│   -> Query Understanding                                    │
│   -> ES Dense Retrieval + ES BM25 Retrieval                 │
│   -> RRF Fusion                                             │
│   -> Optional BGE Rerank                                    │
│   -> Parent Chunk Backfill                                  │
│   -> Domain Knowledge Graph                                 │
│   -> Prompt Context                                         │
│   -> LLM Answer                                             │
│   -> Progress / Reference / Token / Done SSE                │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. 知识入库主流程

### 3.1 文档进入系统

当前主要支持两类入口：

1. 管理端上传 PDF、DOCX、PPTX、Markdown、HTML 等文件。
2. Confluence 单页、Space 或定时增量同步。

入口代码：

- `src/api/knowledge_base_routes.py`
- `src/services/knowledge_ingestion_service.py`
- `src/services/confluence_sync_scheduler_service.py`

### 3.2 建立文档与版本记录

`knowledge_document_registry_service` 为每份知识维护：

- Document：逻辑文档。
- Version：具体内容版本。
- Ingestion Job：本次入库任务。
- Source Metadata：来源、Confluence Page URL、版本号等。
- Ingestion/Index Status：解析和索引状态。

元数据持久化在 MySQL，核心表包括：

- `knowledge_documents`
- `knowledge_document_versions`
- `knowledge_document_chunks`
- `knowledge_ingestion_jobs`
- `rag_manifests`

新版本创建时不会提前替换 `current_version_id`，只有新索引发布成功后才切换。

### 3.3 保存原始文件并统一解析

原始文件先保存到 MinIO，随后由 `document_parser_service` 统一转换为 Markdown：

```text
PDF       -> MinerU，失败时回退 pypdf
DOCX      -> mammoth
PPTX      -> python-pptx
HTML      -> markdownify
MD/TXT    -> passthrough / normalize
DOC/PPT   -> LibreOffice 转换后解析
```

MinIO 同时保留：

1. Raw Blob：原始文件。
2. Parsed Blob：标准化 Markdown。

这样做可以保留原始证据，同时让后续切分流程不必关心源文件格式。

### 3.4 Parent/Child 分块

当前不是简单按固定字符数硬切，而是：

1. 按 Markdown Heading 划分 Section。
2. 保留 `heading_path`。
3. 按段落、列表、表格、图片和代码块聚合。
4. 每个 Section 生成 Parent Chunk。
5. Parent 再切成更小的 Child Chunk。

默认思路：

- Child Chunk 小，适合精准召回。
- Parent Chunk 大，适合给 LLM 提供完整上下文。

当前索引口径是：

- **Elasticsearch 只索引 Child Chunk**。
- **Parent Chunk 存在 MySQL**，并可通过内存/Redis 缓存加速回填。

### 3.5 Embedding 与混合索引

每个 Child Chunk 生成 Embedding，并写入 Elasticsearch 同一个索引：

```text
embedding                              -> Dense Vector 检索
content/title/section_title/...        -> BM25 检索
document_id/version_id/parent_chunk_id -> 过滤和回填
```

默认配置：

- Embedding：`text-embedding-3-small`
- Dimension：`1536`
- ES Index：`document_vector_knowledge`
- Vector Similarity：Cosine

也可切换本地 `BAAI/bge-m3`，但模型和维度改变后必须重建索引。

### 3.6 版本发布

`document_rag_service.publish_version(document_id, version_id)` 负责：

1. 为新版本生成 Chunk 和 Embedding。
2. 写入新版本索引数据。
3. 确认新版本索引成功。
4. 切换 `current_version_id`。
5. 清理旧版本 ES 数据。
6. 更新 MySQL 中的索引状态和时间。

因此版本更新采用“先构建、后切换”的方式，避免用户检索到半成品索引。

---

## 4. 在线问答主流程

### 4.1 接收问题与入口路由

用户可以从以下入口发起问题：

- `POST /chat`
- `POST /mdm-assistant/chat`
- `POST /support-agent/chat`
- `POST /ops-agent/chat`
- Governance Copilot 的知识问答路径

统一聊天入口会先根据 `surface`、意图和场景路由到 Governance、Support 或 Ops。只有需要知识检索的请求才进入 RAG。

### 4.2 Query Understanding

检索前调用：

```python
query_understanding_service.analyze(
    query,
    path_contains,
    chat_history=chat_history,
)
```

主要完成：

1. **多轮问题改写**：结合历史对话补齐指代和上下文。
2. **Query Rewrite**：将原始问题改成更适合语义检索的表达。
3. **Query Expansion**：补充领域缩写、实体别名和相关术语。
4. **Metadata Extraction**：提取表名、Topic、缩写、告警词和实体。
5. **Domain Inference**：判断 governance、ops、architecture 等领域。
6. **Path Shaping**：生成优先检索路径和过滤条件。

输出中的关键字段：

```text
originalQuery
rewrittenQuery        -> Dense Retrieval
retrievalQuery        -> BM25 Retrieval
preferredPathFilters
domainHints
metadata
```

### 4.3 Dense 与 BM25 双路召回

`HybridDocumentRagService.search()` 在同一个 Elasticsearch 索引执行两路检索：

```text
rewrittenQuery
  -> Query Embedding
  -> ES KNN Dense Vector Search

retrievalQuery
  -> ES Multi-match / BM25 Search
```

两路召回互补：

- Dense 擅长语义相似、近义表达和自然语言问题。
- BM25 擅长精确术语、表名、Topic、错误码和缩写。

检索时只查询 `chunk_level=child`，并应用路径和领域过滤。

### 4.4 RRF 融合

Dense 和 BM25 的原始分数不可直接比较，因此使用 RRF（Reciprocal Rank Fusion）按排名融合：

```text
RRF Score = Σ 1 / (k + rank)
```

默认 `k=60`。同一个 Chunk 如果同时被两路命中，会得到更高的融合排名。

### 4.5 可选 BGE Rerank

RRF 得到候选集后，可启用 BGE Cross-Encoder 做精排：

```text
Query + Candidate Chunk
  -> Cross-Encoder
  -> Relevance Score
  -> Reorder
```

Rerank 更准确，但会增加模型加载、CPU/GPU 和响应延迟，因此通过配置开关控制。

### 4.6 Parent Chunk 回填

精排后命中的仍是 Child Chunk。系统根据 `parent_chunk_id` 从 `ParentChunkStore` 获取 Parent：

```text
Child Hit
  -> Memory Cache
  -> Optional Redis Cache
  -> MySQL knowledge_document_chunks
  -> Parent Grounding Content
```

这样既能保持检索精度，又能给 LLM 提供完整段落，减少断章取义。

### 4.7 轻量知识图谱补充

文档检索之外，系统还调用：

```python
domain_knowledge_graph_service.search(query, query_analysis)
```

图谱用于补充 CJS、ESP、ESS、DEC、Contract、Signal、LDM 等领域实体关系。

最终知识上下文包含：

```text
knowledgeDocs      -> 文档证据
knowledgeGraph     -> 实体关系
queryUnderstanding -> 问题理解结果
```

图谱是独立补充通道，不参与 ES 的 RRF 排名。

### 4.8 Prompt 组装与 LLM 生成

上层 Governance、Support、Ops 服务会：

1. 根据意图选择 Prompt 模板。
2. 注入 Parent Grounding Content。
3. 注入知识图谱关系。
4. 注入必要的多轮聊天历史。
5. 要求 LLM 基于证据回答，并避免编造。

LLM 只负责生成答案，不直接操作 Elasticsearch 或 MySQL。

### 4.9 返回进度与引用

流式请求在答案 Token 之前依次返回进度：

```text
intent_recognition
query_rewrite
query_routing
retrieval
rerank
generating
```

引用由 `rag_reference_service` 从最终 `knowledgeDocs` 生成，并按 `documentId` 去重：

```json
{
  "documentId": "...",
  "chunkId": "...",
  "documentTitle": "...",
  "url": "...",
  "path": "...",
  "chunkContent": "...",
  "rerankScore": 0.92,
  "retrievalScore": 0.81
}
```

流式接口通过 SSE 返回：

```text
progress -> reference -> token... -> done
```

非流式接口则通过 `metadata.ragReferences` 返回引用。

---

## 5. 核心数据流

### 5.1 入库数据流

```text
Source
  -> Document/Version/Job Metadata (MySQL)
  -> Raw Blob (MinIO)
  -> Parsed Markdown (MinIO)
  -> Parent Chunks (MySQL)
  -> Child Chunks + Embeddings (Elasticsearch)
  -> Manifest/Index Status (MySQL)
```

### 5.2 查询数据流

```text
Query
  -> Query Understanding
  -> Dense Candidates (ES)
  -> BM25 Candidates (ES)
  -> RRF/Rerank
  -> Parent Content (Cache/MySQL)
  -> Graph Context (JSON Knowledge Graph)
  -> LLM Prompt
  -> Answer + References
```

---

## 6. 核心代码入口

| 阶段 | 主要代码 |
|------|----------|
| API 入库入口 | `src/api/knowledge_base_routes.py` |
| 入库编排 | `src/services/knowledge_ingestion_service.py` |
| 文档注册与版本 | `src/services/knowledge_document_registry_service.py` |
| Blob 存储 | `src/services/document_blob_storage_service.py` |
| 文档解析 | `src/services/document_parser_service.py` |
| Chunking / 索引 / 检索门面 | `src/services/document_rag_service.py` |
| Chunking 实现 | `src/knowledge/chunking.py` |
| ES 索引存储 | `src/knowledge/index_store.py` |
| Dense/BM25/RRF 检索 | `src/knowledge/retrieval.py` |
| Query Understanding | `src/services/query_understanding_service.py` |
| Rerank | `src/services/rag_rerank_service.py` |
| Parent 回填 | `src/services/parent_chunk_store.py` |
| 领域知识图谱 | `src/services/domain_knowledge_graph_service.py` |
| 引用生成 | `src/services/rag_reference_service.py` |
| SSE 进度 | `src/services/chat_rag_progress_service.py` |

---

## 7. 关键设计取舍

### 为什么使用 ES 单引擎混合检索

- Dense 和 BM25 共用一个索引，减少双引擎同步成本。
- 文档版本、路径、领域等过滤条件保持一致。
- 运维和扩容比两套检索后端更简单。

### 为什么只索引 Child Chunk

- Child 更适合精准匹配。
- 避免 Parent 与 Child 同时参与排序造成重复召回。
- Parent 通过 MySQL/缓存回填，职责更清晰。

### 为什么先 Query Understanding

- 原始问题可能包含指代、缩写和领域噪声。
- Dense、BM25 和图谱共享同一份问题理解结果。
- 规则优先的实现可解释、低延迟，避免额外 LLM 调用。

### 为什么图谱不并入 RRF

- 文档 Chunk 与实体关系不是同一种结果。
- 图谱负责关系解释，文档负责事实证据。
- 在 Prompt 层汇合比强行统一打分更容易解释。

---

## 8. 当前实现边界

1. 外部 Confluence、MinIO、MySQL、Redis、Elasticsearch 需要按环境配置。
2. Rerank 默认可关闭；启用后需评估延迟和资源消耗。
3. 领域知识图谱是仓库维护的轻量 JSON 图谱，不是 Neo4j 在线图数据库。
4. RAG 质量仍取决于源文档质量、Chunking、Embedding 模型和检索参数。
5. 文档引用能说明回答证据来源，但不能替代业务系统的实时事实校验。

---

## 9. 相关文档

- [Hybrid Retrieval 设计与实现](../../articles/rag/Hybrid_Retrieval_设计与实现.md)
- [RAG Vector Retrieval](../../articles/rag/RAG_Vector_Retrieval.md)
- [RAG Document Chunking](../../articles/rag/RAG_Document_Chunking.md)
- [RAG Rerank](../../articles/rag/RAG_Rerank.md)
- [Knowledge Base Ingestion](../../functions/Knowledge_Base_Ingestion.md)
- [Query Understanding](../../functions/Query_Understanding_共享预处理设计与实现.md)
- [RAG Progress & References](../../functions/RAG_Progress_and_References_设计与实现.md)
- [Knowledge Version and Zero Downtime Update](../../functions/Knowledge_Version_and_Zero_Downtime_Update.md)

**最后更新**：2026-07-27
