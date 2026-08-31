#!/usr/bin/env tsx
/** Smoke: internal reply API (requires npm run dev + BOSS_BRIDGE_SECRET + LLM). */
import { loadEnvFiles } from "./load-env";

loadEnvFiles();

async function main() {
  const { config } = await import("../src/lib/config");
  const base = config.appUrl.replace(/\/$/, "");
  const secret = config.bossBridgeSecret;

  if (!secret) {
    console.error("FAIL: BOSS_BRIDGE_SECRET not set in .env.local");
    process.exit(1);
  }

  const health = await fetch(`${base}/api/health`);
  console.log("health:", health.status, await health.text());

  const bad = await fetch(`${base}/api/internal/reply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      sessionId: "smoke",
      messages: [{ role: "user", content: "介绍一下你的 RAG 项目" }],
    }),
  });
  console.log("reply without secret:", bad.status, await bad.text());
  if (bad.status !== 401) {
    console.error("FAIL: expected 401 without secret");
    process.exit(1);
  }

  const ok = await fetch(`${base}/api/internal/reply`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-bridge-secret": secret,
    },
    body: JSON.stringify({
      channel: "boss",
      sessionId: "smoke-boss",
      messages: [{ role: "user", content: "介绍一下你的 GDS 知识问答和 RAG 项目经历" }],
      meta: { bossName: "测试HR", company: "测试公司" },
    }),
  });
  const body = await ok.json();
  console.log("reply with secret:", ok.status, JSON.stringify(body, null, 2));

  if (!ok.ok || !body.reply || body.blocked) {
    console.error("FAIL: internal reply smoke");
    process.exit(1);
  }
  console.log("OK reply length:", body.reply.length, "sources:", body.sources?.length ?? 0);

  const salary = await fetch(`${base}/api/internal/reply`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-bridge-secret": secret,
    },
    body: JSON.stringify({
      channel: "boss",
      sessionId: "smoke-salary",
      messages: [{ role: "user", content: "期望薪资多少？" }],
    }),
  });
  const salaryBody = await salary.json();
  console.log("salary reply:", salary.status, JSON.stringify(salaryBody, null, 2));
  if (salaryBody.blocked || !salaryBody.reply) {
    console.error("FAIL: salary should be auto-answered, not blocked");
    process.exit(1);
  }
  if (!/30|35/.test(salaryBody.reply)) {
    console.error("FAIL: salary reply should mention 30/35");
    process.exit(1);
  }

  const blocked = await fetch(`${base}/api/internal/reply`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-bridge-secret": secret,
    },
    body: JSON.stringify({
      channel: "boss",
      sessionId: "smoke-blocked",
      messages: [{ role: "user", content: "方便加个微信吗？" }],
    }),
  });
  const blockedBody = await blocked.json();
  console.log("wechat blocked:", blocked.status, JSON.stringify(blockedBody, null, 2));
  if (!blockedBody.blocked) {
    console.error("FAIL: wechat exchange should be blocked");
    process.exit(1);
  }
  console.log("PASS: internal reply smoke");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
