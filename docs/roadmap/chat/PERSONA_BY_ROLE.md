# 按岗位的人格与知识库偏好（待实现）

> 规格占位。实现前 Agent 默认无 persona，检索全库；实现后按 **会话/分享链接** 绑定轨道。

## 背景

用户面试 **两条岗位线**，回答侧重点不同：

| Persona ID | 岗位 | 简历真源 |
|------------|------|----------|
| `backend-agent` | 后端 + Agent | `08-简历参考/简历-后端AI方向.md` |
| `data-agent` | 数据开发 + Agent | `08-简历参考/简历-数据开发+ai.md` |

同一事实库，不同 **人格口吻 + 检索加权 + system prompt**。

## 目标行为

1. **人格（Persona）**
   - 后端轨：强调 Java、高并发、DDD、抽奖引擎、RAG 平台工程、Agent 编排
   - 数据轨：强调 Flink、Contract、MDM、特征平台、血缘、Lag 治理
   - 共用：诚实、有依据、敏感话题拒答

2. **知识库偏好（Retrieval bias）**
   - 后端轨：提升 `03-项目经历-在职/营销*`、`eda*`、`gds-rag*`、`gds-agents*` 权重；降权 FESS 长文
   - 数据轨：提升 `gds-data-pipeline*`、`fess*`、`cjs*`、`06-原始资料-gds` 中数据相关；降权抽奖算法细节
   - 实现选项：分 collection / 检索时 `persona` 标签过滤 / rerank 加权

3. **入口**
   - 分享链接创建时选择 persona（管理台）
   - Boss bridge `meta.jobTrack` 或配置默认 persona
   - API：`POST /api/v1/chat { persona: "backend-agent" | "data-agent" }`

## 待实现任务

- [ ] SPEC：`docs/PERSONAL_HR_AGENT_SPEC.md` 增加 persona 条款
- [ ] 数据模型：share link / session 存 `personaId`
- [ ] `src/lib/prompt.ts`：`getSystemPrompt(personaId)`
- [ ] `src/lib/rag.ts`：`retrieve(query, { personaId, topK })` 加权或过滤
- [ ] 管理台：创建链接时选「后端轨 / 数据轨」
- [ ] 评测：`evals/golden.jsonl` 分 persona 子集
- [ ] Boss：`boss-bridge` 配置 `DEFAULT_PERSONA=backend-agent`

## 非目标（一阶段）

- 自动从 JD 文本识别 persona（可 P2）
- 每家公司定制 persona（过多）

## 依赖

- 知识库真源已双轨：`personal-knowledge/08-简历参考/`
- 本地布局：[`LOCAL_LAYOUT.md`](./LOCAL_LAYOUT.md)
