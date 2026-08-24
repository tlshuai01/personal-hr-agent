import { z } from "zod";
import { config } from "@/lib/config";
import { streamChatCompletion } from "@/lib/llm";
import { formatRetrievedContext, SYSTEM_PROMPT } from "@/lib/prompt";
import { retrieve } from "@/lib/rag";
import { saveChatMessage } from "@/lib/db";
import { incrementMessageCount, validateShareAccess } from "@/lib/share";

export const runtime = "nodejs";

const bodySchema = z.object({
  token: z.string().min(1),
  messages: z
    .array(
      z.object({
        role: z.enum(["user", "assistant"]),
        content: z.string().max(8000),
      }),
    )
    .min(1)
    .max(40),
});

export async function POST(req: Request) {
  let json: unknown;
  try {
    json = await req.json();
  } catch {
    return Response.json({ error: "invalid json" }, { status: 400 });
  }

  const parsed = bodySchema.safeParse(json);
  if (!parsed.success) {
    return Response.json(
      { error: "validation failed", details: parsed.error.flatten() },
      { status: 400 },
    );
  }

  const { token, messages } = parsed.data;
  const access = validateShareAccess(token);
  if (!access.ok) {
    return Response.json(
      { ok: false, code: access.code, message: access.message },
      { status: 403 },
    );
  }

  const lastUser = [...messages].reverse().find((m) => m.role === "user");
  if (!lastUser) {
    return Response.json({ error: "missing user message" }, { status: 400 });
  }

  saveChatMessage(token, "user", lastUser.content);
  incrementMessageCount(token, 1);

  const retrieved = await retrieve(lastUser.content, 8);
  const context = formatRetrievedContext(retrieved);
  const sources = [...new Set(retrieved.map((r) => r.source))].join(",");

  const llmMessages = [
    { role: "system" as const, content: SYSTEM_PROMPT },
    { role: "system" as const, content: context },
    ...messages.map((m) => ({
      role: m.role as "user" | "assistant",
      content: m.content,
    })),
  ];

  try {
    const upstream = await streamChatCompletion(llmMessages, 0.3);
    const reader = upstream.getReader();
    const decoder = new TextDecoder();
    let full = "";

    const stream = new ReadableStream<Uint8Array>({
      async pull(controller) {
        const { done, value } = await reader.read();
        if (done) {
          if (full.trim()) {
            saveChatMessage(token, "assistant", full);
            incrementMessageCount(token, 1);
          }
          controller.close();
          return;
        }
        full += decoder.decode(value, { stream: true });
        controller.enqueue(value);
      },
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-store",
        "X-Retrieved-Sources": sources,
        "X-App-Name": config.appName,
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "llm error";
    return Response.json({ error: message }, { status: 502 });
  }
}
