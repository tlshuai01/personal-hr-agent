import { validateShareAccess } from "@/lib/share";

export const runtime = "nodejs";

export async function GET(
  _req: Request,
  ctx: { params: Promise<{ token: string }> },
) {
  const { token } = await ctx.params;
  const access = validateShareAccess(token);
  if (!access.ok) {
    return Response.json(
      { ok: false, code: access.code, message: access.message },
      { status: 403 },
    );
  }
  const { link } = access;
  return Response.json({
    ok: true,
    label: link.label,
    expiresAt: link.expires_at,
    maxMessages: link.max_messages,
    messageCount: link.message_count,
  });
}
