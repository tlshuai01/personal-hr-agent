import { NextResponse } from "next/server";
import { config } from "@/lib/config";
import { loadKnowledgeIndex } from "@/lib/rag";

export const runtime = "nodejs";

export async function GET() {
  const index = loadKnowledgeIndex();
  return NextResponse.json({
    ok: true,
    appName: config.appName,
    knowledge: index
      ? {
          chunkCount: index.chunks.length,
          embeddingMode: index.embeddingMode,
          createdAt: index.createdAt,
        }
      : null,
    llm: {
      baseURL: config.llmBaseUrl,
      model: config.llmModel,
    },
  });
}
