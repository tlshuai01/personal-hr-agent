# 知识库填写指南

本目录是 HR Agent 的**唯一事实源**。分类规划见：[`docs/roadmap/knowledge/TAXONOMY.md`](../docs/roadmap/knowledge/TAXONOMY.md)

修改后请执行：

```bash
npm run knowledge:index
npm run eval:retrieval
```

## 索引规则

- `README.md` **不会**被索引
- 子目录下所有 `.md` **会**递归索引（除 README）
- `boundaries.md` 同时在 system prompt 中强调；内容勿与其它文件矛盾

## 推荐目录（待你逐步补齐）

```
knowledge/
├── boundaries.md          ✅ 已有
├── profile.md             ✅ 已有（可合并进 basics/identity）
├── resume.md              ✅ 已有（建议改为 career 时间线的摘要）
├── basics/                ⬜ 待建 — 学历、离职口径、求职意向
├── career/                ⬜ 待建 — 按公司分段经历
├── projects/              ✅ 已有
├── skills.md / stories.md / faq.md   ✅ 已有
└── source-docs/           ✅ 已有（长文备查）
```

## 当前缺口（优先填）

1. **学历** → `basics/education.md`
2. **按公司的时间线** → `career/timeline.md` + 各段经历
3. **离职/看机会原因（口径版）** → `basics/leaving-narrative.md`
4. **到岗与城市** → `basics/availability.md`
5. Boss 真实收到的问题 → 补充进 `faq.md`

## 涉密与口径

- 真正机密：账号、密钥、客户隐私 → 不写或 `boundaries.md` 拒答
- 容量/QPS/成本：个人估算 **可以** 写进项目文档
- 薪资：可写区间或「面议」；Boss 自动回复仍建议拦截具体数字
