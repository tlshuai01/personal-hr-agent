import { timingSafeEqual } from "crypto";
import { config } from "./config";

export function verifyOwnerPassword(input: string | null | undefined): boolean {
  if (!input) return false;
  const expected = config.ownerPassword;
  const a = Buffer.from(input);
  const b = Buffer.from(expected);
  if (a.length !== b.length) return false;
  return timingSafeEqual(a, b);
}

export function getOwnerPasswordFromRequest(req: Request): string | null {
  const header = req.headers.get("x-owner-password");
  if (header) return header;
  const auth = req.headers.get("authorization");
  if (auth?.toLowerCase().startsWith("bearer ")) {
    return auth.slice(7).trim();
  }
  return null;
}
