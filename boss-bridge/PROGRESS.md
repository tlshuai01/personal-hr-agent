# Boss Bridge 试行进展

> 本地进度记录（个人试用，非官方 API）

## 当前状态

| 阶段 | 状态 | 说明 |
|------|------|------|
| **C0** | **已通过** | Cookie 登录 OK；沟通列表可拉取（约 300 会话） |
| **C1** | 未跑 | dry-run，需 `npm run dev` + LLM + `BOSS_BRIDGE_SECRET` |
| **C2** | 未开 | 自动发送，确认 C1 后再开 |
| **C3** | 未开 | 多轮历史 |

更新日期：2026-08-25

## C0 结论

1. **登录**：`boss login --cookie-source chrome` 成功（含 `__zp_stoken__`、`zp_at`）。
2. **不要用 F12 抄 Cookie**：Boss 页面对 DevTools 有反调试；用 boss-cli 从浏览器抽 Cookie 或 `--qrcode`。
3. **列表坑**：`getGeekFriendList.json` **必须带 `page=1`**。上游 `boss chat` 不传 `page` 时返回空 `zpData`；bridge 已改为直接 HTTP 分页拉取。
4. **PATH**：Windows 上 `boss.exe` 可能不在 PATH，需把  
   `%LocalAppData%\Python\pythoncore-3.14-64\Scripts` 加入 PATH，或写全路径。

## 下一步（C1）

```bash
# 根目录 .env.local：LLM_* + BOSS_BRIDGE_SECRET
npm run dev

cd boss-bridge
# .env 中 BOSS_BRIDGE_SECRET 与上面一致
python main.py --phase c1
```

观察日志中的 `[DRY-RUN]` / `[BLOCKED]`，**不要**急着开 C2。

## 风险

- 违反平台 ToS 可能封号；接口随时变更。
- Cookie / `__zp_stoken__` 会过期，需 `boss logout && boss login` 刷新。
