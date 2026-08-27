# 本地个人知识库布局

真源路径（**永不提交 Git**）：

```
C:\Users\tl_94\PycharmProjects\personal-knowledge\
├── 08-简历参考/              ★ 双轨简历真源（后端AI / 数据开发+ai）
├── 01-基本信息/              含 job-search 双轨说明
├── 03-项目经历-在职/         按简历拆分的讲法摘要
└── _meta/resume-canonical.md  矛盾与真源登记
```

## 面试双轨

| Persona（待实现） | 简历 |
|-------------------|------|
| `backend-agent` | `08-简历参考/简历-后端AI方向.md` |
| `data-agent` | `08-简历参考/简历-数据开发+ai.md` |

规格：[`chat/PERSONA_BY_ROLE.md`](../chat/PERSONA_BY_ROLE.md)

## 与应用的关系

```env
KNOWLEDGE_DIR=C:/Users/tl_94/PycharmProjects/personal-knowledge
```

```bash
npm run knowledge:index
python scripts/setup-personal-knowledge.py   # 同步 Obsidian/GDS/简历
```
