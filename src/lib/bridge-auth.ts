import { timingSafeEqual } from "crypto";
import { config } from "./config";

export function verifyBridgeSecret(input: string | null | undefined): boolean {
  if (!input || !config.bossBridgeSecret) return false;
  const a = Buffer.from(input);
  const b = Buffer.from(config.bossBridgeSecret);
  if (a.length !== b.length) return false;
  return timingSafeEqual(a, b);
}

export function getBridgeSecretFromRequest(req: Request): string | null {
  const header = req.headers.get("x-bridge-secret");
  if (header) return header;
  const auth = req.headers.get("authorization");
  if (auth?.toLowerCase().startsWith("bearer ")) {
    return auth.slice(7).trim();
  }
  return null;
}
