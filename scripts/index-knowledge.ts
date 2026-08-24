import { loadEnvFiles } from "./load-env";

async function main() {
  loadEnvFiles();
  const { buildKnowledgeIndex } = await import("../src/lib/rag");
  const index = await buildKnowledgeIndex();
  console.log(
    `Indexed ${index.chunks.length} chunks (mode=${index.embeddingMode}) -> data/index.json`,
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
