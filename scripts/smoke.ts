import fs from "fs";
import path from "path";
import { loadEnvFiles } from "./load-env";

async function main() {
  loadEnvFiles();
  process.env.DATABASE_PATH = path.resolve("data/smoke-app.json");
  if (fs.existsSync(process.env.DATABASE_PATH)) {
    fs.unlinkSync(process.env.DATABASE_PATH);
  }

  const { buildKnowledgeIndex, retrieve } = await import("../src/lib/rag");
  const {
    createShareLink,
    validateShareAccess,
    revokeShareLink,
    linkStatus,
    incrementMessageCount,
  } = await import("../src/lib/share");
  const { readDb, writeDb } = await import("../src/lib/db");

  const index = await buildKnowledgeIndex();
  if (index.chunks.length <= 5) {
    throw new Error(`chunkCount too small: ${index.chunks.length}`);
  }
  console.log(`OK index chunks=${index.chunks.length}`);

  const hits = await retrieve("RAG 混合检索 Hybrid Elasticsearch Agent", 8);
  const joined = hits.map((h) => h.source + h.text).join("\n");
  if (!/rag|检索|agent|知识|治理|运维/i.test(joined)) {
    throw new Error("retrieval did not hit project-related docs");
  }
  console.log(`OK retrieval top=${hits[0]?.source}`);

  const link = createShareLink({
    label: "smoke",
    expiresInHours: 1,
    maxMessages: 2,
  });
  let v = validateShareAccess(link.token);
  if (!v.ok) throw new Error("expected active");
  console.log("OK share active");

  incrementMessageCount(link.token, 2);
  v = validateShareAccess(link.token);
  if (v.ok || v.code !== "limit_reached") {
    throw new Error("expected limit_reached");
  }
  console.log("OK share limit_reached");

  // reset count to test revoke
  const db = readDb();
  const row = db.share_links.find((l) => l.token === link.token)!;
  row.message_count = 0;
  writeDb(db);
  revokeShareLink(link.token);
  v = validateShareAccess(link.token);
  if (v.ok || v.code !== "revoked") throw new Error("expected revoked");
  console.log("OK share revoked");

  const expired = createShareLink({
    label: "expired",
    expiresInHours: 1,
    maxMessages: 10,
  });
  const db2 = readDb();
  const erow = db2.share_links.find((l) => l.token === expired.token)!;
  erow.expires_at = new Date(Date.now() - 1000).toISOString();
  writeDb(db2);
  v = validateShareAccess(expired.token);
  if (v.ok || v.code !== "expired") throw new Error("expected expired");
  if (linkStatus(erow) !== "expired") throw new Error("status mismatch");
  console.log("OK share expired");

  console.log("SMOKE PASS");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
