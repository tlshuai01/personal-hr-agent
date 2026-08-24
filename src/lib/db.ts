import fs from "fs";
import path from "path";
import { config } from "./config";

export type ShareLink = {
  id: number;
  token: string;
  label: string;
  expires_at: string;
  max_messages: number | null;
  message_count: number;
  revoked: 0 | 1;
  created_at: string;
  last_used_at: string | null;
};

export type ChatMessageRow = {
  id: number;
  share_token: string;
  role: string;
  content: string;
  created_at: string;
};

export type DbShape = {
  nextLinkId: number;
  nextMessageId: number;
  share_links: ShareLink[];
  chat_messages: ChatMessageRow[];
};

function emptyDb(): DbShape {
  return {
    nextLinkId: 1,
    nextMessageId: 1,
    share_links: [],
    chat_messages: [],
  };
}

export function ensureDataDir(): void {
  const dir = path.dirname(config.databasePath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

export function readDb(): DbShape {
  ensureDataDir();
  if (!fs.existsSync(config.databasePath)) {
    const db = emptyDb();
    writeDb(db);
    return db;
  }
  const raw = fs.readFileSync(config.databasePath, "utf8");
  return JSON.parse(raw) as DbShape;
}

export function writeDb(db: DbShape): void {
  ensureDataDir();
  fs.writeFileSync(config.databasePath, JSON.stringify(db, null, 2), "utf8");
}

export function saveChatMessage(
  shareToken: string,
  role: string,
  content: string,
): ChatMessageRow {
  const db = readDb();
  const row: ChatMessageRow = {
    id: db.nextMessageId++,
    share_token: shareToken,
    role,
    content,
    created_at: new Date().toISOString(),
  };
  db.chat_messages.push(row);
  writeDb(db);
  return row;
}

export function incrementMessageCount(token: string, by = 1): void {
  const db = readDb();
  const link = db.share_links.find((l) => l.token === token);
  if (!link) return;
  link.message_count += by;
  link.last_used_at = new Date().toISOString();
  writeDb(db);
}
