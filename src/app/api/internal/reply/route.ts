import { z } from "zod";
import {
  getBridgeSecretFromRequest,
  verifyBridgeSecret,
} from "@/lib/bridge-auth";
import { generateReply } from "@/lib/reply";

export const runtime = "nodejs";

const bodySchema = z.object({
  channel: z.enum(["boss"]).default("boss"),
  sessionId: z.string().min(1),
  messages: z
    .array(
      z.object({
        role: z.enum(["user", "assistant"]),
        content: z.string().max(8000),
      }),
    )
    .min(1)
    .max(40),
  meta: z
    .object({
      bossName: z.string().optional(),
      company: z.string().optional(),
      jobTitle: z.string().optional(),
      resumeAlreadySent: z.boolean().optional(),
    })
    .optional(),
});

function unauthorized() {
  return Response.json({ error: "unauthorized" }, { status: 401 });
}

export async function POST(req: Request) {
  if (!verifyBridgeSecret(getBridgeSecretFromRequest(req))) {
    return unauthorized();
  }

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

  try {
    const result = await generateReply(parsed.data.messages, {
      channel: "boss",
      meta: parsed.data.meta,
    });
    return Response.json({
      ok: true,
      channel: parsed.data.channel,
      sessionId: parsed.data.sessionId,
      reply: result.reply,
      blocked: result.blocked,
      blockReason: result.blockReason ?? null,
      sources: result.sources,
      actions: result.actions,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "reply error";
    return Response.json({ error: message }, { status: 502 });
  }
}
