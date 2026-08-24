# Hybrid Retrieval 设计与实现

## 1. 当前口径

当前共享检索层的最新实现已经变成：

> **Elasticsearch dense retrieval + Elasticsearch BM25 retrieval + RRF fusion**

也就是：

1. dense 语义召回已经切到 Elasticsearch
2. keyword / BM25 通道也已经收敛到 Elasticsearch
3. 上层 governance / support / ops 继续复用同一个 `search_doc_knowledge` contract

---

## 2. 为什么这样改

当前这层的改造目标是把共享 RAG 收敛成单引擎 hybrid retrieval：

1. dense vector 用 ES `dense_vector`
2. keyword retrieval 用 ES 原生 BM25
3. 保持上层 agent contract 不变
4. 为后续 document-level 增量索引打基础

---

## 3. 当前实现入口

核心文件：

1. `src\services\document_rag_service.py`
2. `src\tools\document_rag_tool.py`

当前 `ragMode()` 返回：

```python
def rag_mode(self) -> str:
    return "hybrid_es_dense_es_bm25"
```

工具层描述也已经切换成：

```python
"Elasticsearch-dense plus Elasticsearch-BM25 hybrid retrieval"
```

---

## 4. 当前查询流程

```text
search_doc_knowledge
  -> query_understanding_service.analyze()
  -> document_rag_service.search()
      -> _ensure_index()
      -> _vector_search()        # Elasticsearch dense
      -> _keyword_search()       # Elasticsearch BM25
      -> _merge_results()        # RRF fusion + optional BGE rerank
      -> parent backfill / coalesce
      -> knowledge graph lookup
      -> return unified chunks
```

---

## 5. 索引设计

当前索引设计是：

1. `Elasticsearch index`
   - `embedding` dense vector
   - `content / title / section_title / heading_path` 这些 text fields 同时承担 BM25
   - 负责语义召回、关键词召回、parent chunk lookup
2. 同一份 chunk metadata 直接保存在 ES 文档里

---

## 6. 当前边界

1. 当前已经不是双后端过渡态，而是 ES-only hybrid retrieval
2. 文档真源已经收口到 registry + MinIO，而不是本地 `ai-doc/` 扫描
3. graph 仍然是独立的 lightweight domain graph，不和检索引擎混成一个系统
4. 索引侧已支持按文档版本做增量 upsert（version / chunk 状态见 MySQL，细节见向量检索主文档）

更详细的设计、代码入口、流程图和实现说明请看：

1. `ai-doc/articles/rag/RAG_Vector_Retrieval.md`
