# 评测路线图

## 已有

- `npm run eval:retrieval` — 黄金集检索 hit@k
- `npm run eval` — LLM 端到端
- `npm run smoke` / `smoke:bridge`

## 待增

- [ ] Boss 高频 HR 问法子集（`evals/boss-golden.jsonl`）
- [ ] blocked 策略单测（薪资/offer/微信）
- [ ] Channel dry-run 回放：保存 Core 输入输出 fixture
- [ ] 回归：索引变更后 retrieval 不低于基线

## 门槛建议

| 指标 | 目标 |
|------|------|
| retrieval 覆盖 | ≥ 90% |
| blocked 误放 | 0（敏感题） |
| C1 dry-run 人工抽检 | 10 条满意再开 C2 |
