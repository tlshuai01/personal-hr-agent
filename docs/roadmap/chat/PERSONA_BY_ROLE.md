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
   - 后端轨：强调 **Java + Python**、高并发、DDD、抽奖引擎、RAG 平台工程、Agent 编排
   - 数据轨：强调 Flink、Contract、MDM、特征平台、血缘、Lag 治理（语言侧可带 Java/Python）
   - 共用：诚实、有依据、敏感话题拒答；**Python 为常用语言**，勿在后端轨话术里只写 Java

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
- [ ] `src/lib/prompt.ts`：`getSystemPrompt(personaId)` — **打招呼文案按轨切换**（勿写死「Java 后端和 Agent / 数据平台」）
  - `backend-agent`：偏 **Java+Python** / Agent / RAG 平台
  - `data-agent`：偏 数据开发 / Flink / 特征 / Agent
- [ ] `src/lib/rag.ts`：`retrieve(query, { personaId, topK })` 加权或过滤
- [ ] 管理台：创建链接时选「后端轨 / 数据轨」
- [ ] 评测：`evals/golden.jsonl` 分 persona 子集
- [ ] Boss：`boss-bridge` 配置 `DEFAULT_PERSONA=backend-agent`

### 按职位选轨（打招呼 / 发哪份简历）— P1

现状：`inferResumeTrack(jobTitle)` 只影响 `actions.send_resume.track`；**开场白仍是通用后端+平台话术**，和数据岗会错位。

- [ ] **选轨输入优先用会话列表字段**（一般**不必**先调 JD 详情接口）
  - 列表已有：`jobName` / `title` / `sourceTitle`（见 friend 归一化）→ 传入 `meta.jobTitle` + 推断 `meta.jobTrack`
  - 规则：职位名含「数据 / Flink / 数仓 / ETL / 特征…」→ `data-agent`；否则默认 `backend-agent`
  - 落本地：`SessionStore` 记 `resumeTrack` / `personaId`，同会话后续一致
- [ ] **话术绑定轨道**：system prompt / 示例开场随 `jobTrack` 变；禁止再输出另一轨的固定自我介绍
  - 后端轨示例方向：「Java / Python 后端和 Agent / RAG 平台」
- [ ] **JD 详情接口 = 可选增强，非必需**
  - 何时再拉：职位名含糊（如「高级开发工程师」「AI 工程师」）或列表字段为空
  - 探测：Boss 职位详情 / `encryptJobId` 一类 API；拿到 JD 文本后再做关键词或轻量分类
  - 仍失败：默认 `backend-agent`，或 dry-run 报告标「轨不确定」人工看
- [ ] 与发简历联动：`send_resume` 的附件与开场自我介绍必须同一轨

### 按 JD 改简历（定制突出项）— P2

双轨简历是基线；**后续应按具体 JD 再改一版侧重点**（不是另造事实）。

- [ ] 输入：职位列表名 +（可选）JD 全文 / 关键词
- [ ] 输出：在对应轨真源上 **重排/加粗/压缩** 相关项目与技能（Java vs Python vs Flink 等），生成投递稿
- [ ] 约束：不得编造经历；改动仅限强调顺序、篇幅、技能排序；真源仍在 `08-简历参考/`
- [ ] 流程建议：dry-run 出「JD→改点 diff」→ 人工确认后再导出 PDF / 发附件
- [ ] 落点：Owner 工具或脚本（如 `scripts/resume-adapt-from-jd.ts`），与 `send_resume.track` 联动

## 非目标（一阶段）

- 每家公司自动无审改定稿（必须人工确认）
- 用完整 JD 做复杂语义匹配 / 多分类模型（列表关键词够用再升级）

## 依赖

- 知识库真源已双轨：`personal-knowledge/08-简历参考/`
- 本地布局：[`../knowledge/LOCAL_LAYOUT.md`](../knowledge/LOCAL_LAYOUT.md)
- Boss 渠道：[`../channels/BOSS.md`](../channels/BOSS.md)（发简历真链路与 `resumeTrack` 持久化）
