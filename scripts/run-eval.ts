import fs from "fs";
import path from "path";
import { loadEnvFiles } from "./load-env";

type Golden = {
  id: string;
  category: string;
  question: string;
  must_include?: string[];
  must_not_include?: string[];
};

async function main() {
  loadEnvFiles();
  const retrievalOnly = process.argv.includes("--retrieval");
  const { retrieve, buildKnowledgeIndex, loadKnowledgeIndex } = await import(
    "../src/lib/rag"
  );
  const { completeChat } = await import("../src/lib/llm");
  const { SYSTEM_PROMPT, formatRetrievedContext } = await import(
    "../src/lib/prompt"
  );

  if (!loadKnowledgeIndex()) {
    await buildKnowledgeIndex();
  }

  const goldenPath = path.resolve("evals/golden.jsonl");
  const lines = fs
    .readFileSync(goldenPath, "utf8")
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);
  const cases = lines.map((l) => JSON.parse(l) as Golden);

  const results: Array<{
    id: string;
    pass: boolean;
    skipped?: boolean;
    detail?: string;
  }> = [];

  for (const c of cases) {
    const hits = await retrieve(c.question, 8);
    const retrievedText = hits.map((h) => h.text).join("\n");

    if (retrievalOnly) {
      if (c.category === "boundary" || c.category === "hallucination") {
        results.push({ id: c.id, pass: true, skipped: true });
        continue;
      }
      const hay = `${hits.map((h) => h.source).join("\n")}\n${retrievedText}`;
      const miss = (c.must_include ?? []).filter((k) => !hay.includes(k));
      const bad = (c.must_not_include ?? []).filter((k) => hay.includes(k));
      const pass = miss.length === 0 && bad.length === 0;
      results.push({
        id: c.id,
        pass,
        detail: pass ? undefined : `miss=${miss}; bad=${bad}`,
      });
      continue;
    }

    const answer = await completeChat(
      [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "system", content: formatRetrievedContext(hits) },
        { role: "user", content: c.question },
      ],
      0.2,
    );
    const miss = (c.must_include ?? []).filter((k) => !answer.includes(k));
    const bad = (c.must_not_include ?? []).filter((k) => answer.includes(k));
    const pass = miss.length === 0 && bad.length === 0;
    results.push({
      id: c.id,
      pass,
      detail: pass ? undefined : `miss=${miss}; bad=${bad}; ans=${answer.slice(0, 120)}`,
    });
  }

  const scored = results.filter((r) => !r.skipped);
  const passed = scored.filter((r) => r.pass).length;
  const rate = scored.length ? passed / scored.length : 0;
  const report = {
    mode: retrievalOnly ? "retrieval" : "llm",
    total: scored.length,
    passed,
    rate,
    results,
    createdAt: new Date().toISOString(),
  };
  fs.mkdirSync("data", { recursive: true });
  fs.writeFileSync("data/eval-report.json", JSON.stringify(report, null, 2));
  console.log(
    `${report.mode} pass ${passed}/${scored.length} (${(rate * 100).toFixed(1)}%)`,
  );
  if (rate < 0.9) {
    console.error("FAIL: pass rate < 90%");
    process.exit(1);
  }
  console.log("EVAL PASS");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
