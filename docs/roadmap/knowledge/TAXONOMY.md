# 个人知识库分类规划

> 目标：RAG + Agent 能**准确、可引用**地回答 HR 关于你背景、经历、项目、动机的问题；无依据则拒答。  
> 原则：**一份事实只写一处**，其它文件链接；`boundaries.md` 优先级最高。

---

## 你现在的库缺什么？

当前 `knowledge/` **强项**：项目理解、技能、STAR、FAQ、边界。  
**缺口**（HR / Boss 高频，检索却容易空）：

| 缺口 | HR 典型问法 | 建议文档 |
|------|-------------|----------|
| 学历与教育 | 什么学校、专业、统招吗 | `basics/education.md` |
| 身份与时间线 | 几年经验、每段公司起止 | `career/timeline.md` + 各段 `career/*.md` |
| 离职原因 | 为什么看机会、为什么离开上一家 | `basics/leaving-narrative.md` |
| 求职动机 | 想看什么方向、为什么选我们 | `basics/job-search.md` |
| 到岗与地点 | 什么时候能入职、接受哪些城市 | `basics/availability.md` |
| 薪资口径 | 期望区间或面议策略 | `basics/compensation.md`（可选；Boss 自动回复仍建议拦截） |
| 个人公开信息 | GitHub、博客、开源 | `basics/public-links.md` |
| 每段工作细节 | 部门规模、汇报线、具体职责 | 各 `career/company-*.md` |
| 非 AI 经历 | 更早的工作/实习 | `career/` 同样覆盖 |
| 证书与荣誉 | 英语、职称、竞赛 | `basics/credentials.md`（如有） |

**离职原因要不要写？**  
**要写，但写「对外口径」**，不写情绪细节、不写可识别他人的负面信息。Agent 只复述口径 bullets；具体数字、撕扯细节仍走 `boundaries.md` 或人工聊。

---

## 推荐目录结构（三层）

```
knowledge/
├── README.md                 # 维护说明 + 文件清单（不索引）
├── boundaries.md             # L0 边界（最高优先级，已有）
│
├── basics/                   # L1 人与求职（HR 第一轮）
│   ├── identity.md           # 姓名、城市、总工龄、一句话定位
│   ├── education.md          # 学历、专业、起止年
│   ├── job-search.md         # 意向方向、公司类型、团队偏好
│   ├── leaving-narrative.md  # 离职/看机会原因（口径版）
│   ├── availability.md       # 到岗时间、出差/远程、城市
│   ├── compensation.md       # 薪资区间或「面议」策略（可选）
│   ├── public-links.md       # GitHub、作品集（可公开部分）
│   └── credentials.md        # 证书/语言（可选）
│
├── career/                   # L2 职业时间线（按公司/阶段）
│   ├── timeline.md           # 总表：公司 | 职位 | 起止 | 一句话
│   ├── 01-company-a.md       # 按时间倒序编号或公司名
│   ├── 02-company-b.md
│   └── ...
│
├── projects/                 # L3 项目深度（已有，与技术面试共用）
│   └── *.md
│
├── skills.md                 # L4 能力矩阵（已有）
├── stories.md                # L4 STAR 故事（已有）
├── faq.md                    # L4 高频问答（已有，可链到上面各文件）
├── resume.md                 # 可选：对外简历纯文本镜像
│
└── source-docs/              # L5 原始长文（低优先级或面试深挖）
    └── ...
```

### 层级含义

| 层 | 用途 | 检索权重建议 |
|----|------|--------------|
| L0 boundaries | 什么绝对不能乱说 | prompt 固定注入，不单靠检索 |
| L1 basics | Boss 招呼、HR 筛简历 | 高 |
| L2 career | 「你在 XX 做了什么」 | 高 |
| L3 projects | 技术深挖、架构 | 高（你已有） |
| L4 skills/stories/faq | 归纳与口语化 | 中 |
| L5 source-docs | 细节备查 | 中低，避免淹没 basics |

---

## 各文件写什么（模板要点）

### `basics/identity.md`

```markdown
# 基本信息
- 姓名：（对外是否用全名）
- 现居城市：
- 总工龄：X 年（截至 YYYY-MM）
- 当前状态：在职看机会 / 离职交接中 / …
- 一句话定位：（与 profile 一致，可更短）
- 联系方式策略：Agent 不自动给微信/电话，引导 HR 平台内沟通
```

### `basics/education.md`

```markdown
# 教育背景
## 最高学历
- 学校：
- 专业：
- 学历：本科/硕士…
- 起止：
- 是否统招：（如适用）
## 补充说明（可选）
- 与现岗位的关联：…
```

### `basics/leaving-narrative.md`（重要）

分三块，**只写你愿意让 Agent 复述的内容**：

```markdown
# 离职与看机会（对外口径）

## 当前看机会的原因（1～3 条，积极中性）
- 例：希望在 Agent/RAG 方向承担更完整的平台职责
- 例：现团队方向调整，与个人长期规划不一致

## 对上一家（客观事实，不点名批评）
- 例：完成了 XX 类项目，因组织原因寻求新平台

## Agent 不要展开的话题
- 具体补偿、人际冲突、未公开组织变动
- 见 boundaries.md
```

### `career/timeline.md`

一张总表，便于回答「介绍一下经历」：

| 时间段 | 公司 | 职位 | 核心职责（一行） | 详情文件 |
|--------|------|------|------------------|----------|
| 20xx–20xx | A | 后端/Agent | … | `01-company-a.md` |

### `career/01-company-a.md`（每段经历）

```markdown
# 公司 A · 职位 · 20xx–20xx

## 公司与业务（一句话，可公开）
## 我的角色
- 汇报关系 / 团队规模（若可讲）
## 主要职责（3～5 条）
## 代表性成果（可量化，个人估算注明口径）
## 使用技术栈
## 与 projects/ 的对应关系
- 详见 projects/knowledge-rag-platform.md
## 离职原因（本段）
- 链到 leaving-narrative 或写本段一句口径
```

### `projects/*.md`（已有）

保持「一个项目一篇」：背景、你的角色、架构、难点、结果、**个人负责边界**（避免说成全团队功劳或一人包办）。

---

## 与 Chat / Boss 的关系

- **Core RAG** 只读 `knowledge/`，不区分 Boss / 网页。
- **Boss 渠道** 对薪资/offer/联系方式自动拦截；**离职原因、学历** 可以答，但内容必须来自 `basics/`、`career/`，不能临场编造。
- 网页分享链接与 Boss 共用同一知识库；Owner 更新 md → `npm run knowledge:index`。

---

## 填写顺序建议

1. `basics/identity.md` + `education.md`  
2. `career/timeline.md` + **最近 1～2 段** `career/*.md`  
3. `basics/leaving-narrative.md` + `job-search.md` + `availability.md`  
4. 核对 `projects/` 与 career 交叉链接  
5. 扩展 `faq.md`（把 Boss 上真实收到的问题加进去）  
6. `npm run knowledge:index` → `npm run eval:retrieval`  

---

## 评测：怎么算「库够了」

在 `evals/golden.jsonl` 增加 HR 向问题，例如：

- 学历与专业？
- 为什么离开上一家？（应命中 `leaving-narrative`）
- 每段工作分别做什么？
- 最快什么时候到岗？
- 期望 base 多少？（应 blocked 或命中 compensation 面议口径）

检索覆盖 **≥90%** 再开 Boss C1 大规模 dry-run。

---

## 维护约定

- 修改任意 md → `npm run knowledge:index`
- 真实姓名、电话、身份证：**不要**入库；用「平台内沟通」策略
- 容量/QPS/成本：个人估算可保留（见 boundaries）
- 新增分类先在本文件登记，再建 md
