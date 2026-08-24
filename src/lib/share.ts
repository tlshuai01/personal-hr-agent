import { randomBytes } from "crypto";
import {
  type ShareLink,
  incrementMessageCount,
  readDb,
  writeDb,
} from "./db";
import { config } from "./config";

export type ShareStatus = "active" | "revoked" | "expired" | "limit_reached";

export type ValidateFailCode =
  | "not_found"
  | "revoked"
  | "expired"
  | "limit_reached";

export function createToken(): string {
  return randomBytes(24).toString("base64url");
}

export function linkStatus(link: ShareLink, now = new Date()): ShareStatus {
  if (link.revoked === 1) return "revoked";
  if (now >= new Date(link.expires_at)) return "expired";
  if (
    link.max_messages != null &&
    link.message_count >= link.max_messages
  ) {
    return "limit_reached";
  }
  return "active";
}

export function validateShareAccess(
  token: string,
):
  | { ok: true; link: ShareLink }
  | { ok: false; code: ValidateFailCode; message: string } {
  const db = readDb();
  const link = db.share_links.find((l) => l.token === token);
  if (!link) {
    return { ok: false, code: "not_found", message: "分享链接不存在" };
  }
  const status = linkStatus(link);
  if (status === "revoked") {
    return { ok: false, code: "revoked", message: "分享链接已作废" };
  }
  if (status === "expired") {
    return { ok: false, code: "expired", message: "分享链接已过期" };
  }
  if (status === "limit_reached") {
    return {
      ok: false,
      code: "limit_reached",
      message: "该链接消息数已达上限",
    };
  }
  return { ok: true, link };
}

export function createShareLink(opts: {
  label: string;
  expiresInHours?: number;
  maxMessages?: number | null;
}): ShareLink & { url: string } {
  const db = readDb();
  const hours = opts.expiresInHours ?? 72;
  const expires = new Date(Date.now() + hours * 3600 * 1000);
  const link: ShareLink = {
    id: db.nextLinkId++,
    token: createToken(),
    label: opts.label || "未命名",
    expires_at: expires.toISOString(),
    max_messages: opts.maxMessages === undefined ? 100 : opts.maxMessages,
    message_count: 0,
    revoked: 0,
    created_at: new Date().toISOString(),
    last_used_at: null,
  };
  db.share_links.unshift(link);
  writeDb(db);
  return { ...link, url: `${config.appUrl}/c/${link.token}` };
}

export function revokeShareLink(token: string): boolean {
  const db = readDb();
  const link = db.share_links.find((l) => l.token === token);
  if (!link) return false;
  link.revoked = 1;
  writeDb(db);
  return true;
}

export function listShareLinks(): Array<ShareLink & { url: string; status: ShareStatus }> {
  const db = readDb();
  return db.share_links.map((link) => ({
    ...link,
    url: `${config.appUrl}/c/${link.token}`,
    status: linkStatus(link),
  }));
}

export { incrementMessageCount };
