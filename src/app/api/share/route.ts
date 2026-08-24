import { z } from "zod";
import { getOwnerPasswordFromRequest, verifyOwnerPassword } from "@/lib/auth";
import {
  createShareLink,
  listShareLinks,
  revokeShareLink,
} from "@/lib/share";

export const runtime = "nodejs";

function unauthorized() {
  return Response.json({ error: "unauthorized" }, { status: 401 });
}

function requireOwner(req: Request): boolean {
  return verifyOwnerPassword(getOwnerPasswordFromRequest(req));
}

export async function GET(req: Request) {
  if (!requireOwner(req)) return unauthorized();
  return Response.json({ links: listShareLinks() });
}

const createSchema = z.object({
  label: z.string().min(1).max(200),
  expiresInHours: z.number().positive().max(24 * 30).optional(),
  maxMessages: z.number().int().positive().nullable().optional(),
});

export async function POST(req: Request) {
  if (!requireOwner(req)) return unauthorized();
  let json: unknown;
  try {
    json = await req.json();
  } catch {
    return Response.json({ error: "invalid json" }, { status: 400 });
  }
  const parsed = createSchema.safeParse(json);
  if (!parsed.success) {
    return Response.json({ error: "validation failed" }, { status: 400 });
  }
  const link = createShareLink(parsed.data);
  return Response.json({ link }, { status: 201 });
}

const deleteSchema = z.object({
  token: z.string().min(1),
});

export async function DELETE(req: Request) {
  if (!requireOwner(req)) return unauthorized();
  let json: unknown;
  try {
    json = await req.json();
  } catch {
    return Response.json({ error: "invalid json" }, { status: 400 });
  }
  const parsed = deleteSchema.safeParse(json);
  if (!parsed.success) {
    return Response.json({ error: "validation failed" }, { status: 400 });
  }
  const ok = revokeShareLink(parsed.data.token);
  if (!ok) return Response.json({ error: "not found" }, { status: 404 });
  return Response.json({ ok: true });
}
