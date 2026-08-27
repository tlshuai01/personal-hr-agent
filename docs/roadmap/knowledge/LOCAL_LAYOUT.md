# 本地个人知识库布局

真源路径（**永不提交 Git**）：

```
C:\Users\tl_94\PycharmProjects\personal-knowledge\
├── README.md
├── _meta/                    # 矛盾口径、维护说明
├── 01-基本信息/              # 身份、学历、求职、离职、到岗
├── 02-工作经历/              # 时间线、各公司
├── 03-项目经历-在职/         # eBay / 爱立信真实项目
├── 04-项目经历-架构理解/     # RAG/治理/Ops 个人理解
├── 05-技能与问答/            # skills / FAQ / boundaries
├── 06-原始资料-gds/          # 从 gds-ai-experience/docs 复制
└── 07-原始资料-obsidian/     # 从 Obsidian 复制的主简历等
```

## 与应用的关系

```env
# personal-hr-agent/.env.local
KNOWLEDGE_DIR=C:/Users/tl_94/PycharmProjects/personal-knowledge
```

```bash
npm run knowledge:index
```

## 重新同步 Obsidian / GDS

```bash
python scripts/setup-personal-knowledge.py
```

会**覆盖**已映射文件；`_meta/` 与 `03-项目经历-在职/` 手写文件请备份。

## 分类原则

| 层 | 用途 |
|----|------|
| 01–02 | HR 第一轮：是谁、在哪干过 |
| 03 | 真实项目（面试主战场） |
| 04 | 架构理解（与 gds-ai-experience 对齐） |
| 05 | Agent 策略 + 口述 |
| 06–07 | 长文备查，检索优先级低于 01–03 |

矛盾统一：`_meta/conflicts-resolved.md`
