import path from "path";

function env(name: string, fallback = ""): string {
  return process.env[name]?.trim() || fallback;
}

export const config = {
  ownerPassword: env("OWNER_PASSWORD", "change-me"),
  llmBaseUrl: env("LLM_BASE_URL", "http://127.0.0.1:11434/v1"),
  llmApiKey: env("LLM_API_KEY", "ollama"),
  llmModel: env("LLM_MODEL", "qwen2.5"),
  embeddingBaseUrl: env("EMBEDDING_BASE_URL"),
  embeddingApiKey: env("EMBEDDING_API_KEY", "ollama"),
  embeddingModel: env("EMBEDDING_MODEL"),
  appName: env("NEXT_PUBLIC_APP_NAME", "个人介绍助手"),
  appUrl: env("APP_URL", "http://localhost:3000").replace(/\/$/, ""),
  databasePath: path.resolve(process.cwd(), env("DATABASE_PATH", "data/app.json")),
  knowledgeIndexPath: path.resolve(
    process.cwd(),
    env("KNOWLEDGE_INDEX_PATH", "data/index.json"),
  ),
  knowledgeDir: path.resolve(
    process.cwd(),
    env("KNOWLEDGE_DIR", "C:/Users/tl_94/PycharmProjects/personal-knowledge"),
  ),
  bossBridgeSecret: env("BOSS_BRIDGE_SECRET"),
};

export function useApiEmbedding(): boolean {
  return Boolean(config.embeddingBaseUrl && config.embeddingModel);
}
