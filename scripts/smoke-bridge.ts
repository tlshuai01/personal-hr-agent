#!/usr/bin/env tsx
/** Smoke: internal reply API (requires npm run dev + BOSS_BRIDGE_SECRET + LLM). */
import { loadEnvFiles } from "./load-env";
import { config } from "../src/lib/config";

loadEnvFiles();

const base = config.appUrl.replace(/\/$/, "");
const secret = config.bossBridgeSecret;

async function main() {
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

  const ok = await fetch(`${base}/api/internal/reply`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-bridge-secret": secret,
    },
    body: JSON.stringify({
      channel: "boss",
      sessionId: "smoke-boss",
      messages: [{ role: "user", content: "介绍一下你的 RAG 项目经历" }],
      meta: { bossName: "测试HR", company: "测试公司" },
    }),
  });
  const body = await ok.json();
  console.log("reply with secret:", ok.status, JSON.stringify(body, null, 2));

  if (!ok.ok || !body.reply) {
    console.error("FAIL: internal reply smoke");
    process.exit(1);
  }
  console.log("PASS: internal reply smoke");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
