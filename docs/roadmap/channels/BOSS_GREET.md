# 主动搜职位 + 打招呼（规划）

> 状态：**G0 进行中**（搜岗 + dry-run 拟打招呼）  
> 更新：2026-09-01  
> 参考：`boss-bridge/_ref/zhipin-geek/`（`search` / `greet` / `batch-greet`）

## 目标

主动按关键词/城市搜职位（或拉推荐），对合适职位**打招呼**开聊；开场话术按 **后端轨 / 数据轨** 区分，并与发简历选轨一致。  
后续由 C2 接手对方回复。

## 与现有阶段关系

| 阶段 | 职责 |
|------|------|
| **G0–G2（本能力）** | 搜岗 → 筛选 → 打招呼（开会话） |
| **C1/C2** | 已开聊会话的回复 / 发简历 |
| **日程（S0）** | 约到面试后再记日历 |

## 分阶段

### G0 — 搜岗 + dry-run（当前）

- [x] HTTP：`GET /wapi/zpgeek/search/joblist.json`（Referer 对齐 geek/job）
- [x] 归一化职位卡：`jobName` / `brandName` / `salaryDesc` / `securityId` / `lid`
- [x] 按职位名推断 `jobTrack`（复用 `resume_select.infer_job_track`）
- [x] 按轨生成**拟打招呼文案**（本地模板，不经 LLM；后续可接 Core）
- [x] CLI：`python scripts/search_and_greet.py "关键词" --city 上海 -n 5`（默认 dry-run）
- [x] 审计：`reports/audit/greet-YYYY-MM-DD.md` + `.jsonl`
- [x] 本地去重：`data/greeted.json`（已打招呼的 `securityId`）

### G1 — 真打招呼（闸门）

- [x] Transport：`greet()` → `GET /wapi/zpgeek/friend/add.json`
- [x] `BOSS_ENABLE_GREET=true` 才允许 `--force`（默认 false）
- [x] 限速：`GREET_DELAY_SEC`（默认 1.5s）
- [ ] 每日上限 `GREET_DAILY_LIMIT`
- [ ] 可选：打招呼成功后 MQTT 补发「按轨开场」自定义一句

### G2 — 产品化

- [ ] 推荐职位：`geekGetJob?tag=5`
- [ ] 过滤：薪资/经验/学历参数；跳过外包敏感词（可配置）
- [ ] Core：`/api/internal/reply` 生成个性化开场（带 job meta）
- [ ] 与 Persona / 发简历轨强制一致
- [ ] 管理台或配置文件维护搜索计划（多关键词轮转）

## 风控

- 默认 **dry-run**；真发需显式 env + `--force`
- 不要高频扫全网；优先少而准
- 违反 Boss ToS 有封号风险——个人试用自负

## 命令（G0/G1）

策略文件：[`boss-bridge/greet_config.json`](../../../boss-bridge/greet_config.json)

- 活跃时段：`active_hours`（默认 09:00–18:00，本机时间）
- 薪资：`min_salary_k`（默认 20）
- 跳过词：`skip_keywords`（日结 / 实习 / …）
- 关键词列表：`queries`

```bash
cd boss-bridge
# 按配置 dry-run（非活跃时段会跳过；夜间调试加 --ignore-hours）
.\.venv\Scripts\python scripts/search_and_greet.py --ignore-hours

# 活跃时段内循环搜岗+打招呼（真发需 BOSS_ENABLE_GREET=true）
.\.venv\Scripts\python scripts/search_and_greet.py --loop --force
```

## 验收

| 阶段 | 标准 |
|------|------|
| G0 | 搜索返回职位列表；每条有 track + 拟文案；写入 audit；不调用 friend/add |
| G1 | `--force` 成功打出招呼；重复 securityId 跳过；audit 记 `greeted` |
| G2 | 推荐源 + 日限额 + 可选 LLM 开场 |
