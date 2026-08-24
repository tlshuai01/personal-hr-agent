import fs from "fs";
import path from "path";
import OpenAI from "openai";
import { config, useApiEmbedding } from "./config";

export type KnowledgeChunk = {
  id: string;
  source: string;
  text: string;
  embedding: number[];
};

export type KnowledgeIndex = {
  version: 1;
  createdAt: string;
  embeddingMode: "api" | "local";
  chunks: KnowledgeChunk[];
};

export type RetrievedChunk = {
  source: string;
  text: string;
  score: number;
  id: string;
};

const LOCAL_DIM = 384;
const MAX_CHARS = 800;

const STOPWORDS = new Set([
  "的",
  "了",
  "吗",
  "呢",
  "啊",
  "吧",
  "你",
  "我",
  "他",
  "她",
  "它",
  "是",
  "在",
  "有",
  "和",
  "与",
  "或",
  "什么",
  "怎么",
  "如何",
  "有没有",
  "分别",
  "一下",
  "这个",
  "那个",
  "哪些",
  "可以",
  "能够",
  "请",
  "问",
  "下",
]);

function tokenize(text: string): string[] {
  const matches = text.toLowerCase().match(/[\u4e00-\u9fff]|[a-zA-Z0-9_]+/g);
  return matches ?? [];
}

function fnvHash(token: string): number {
  let h = 2166136261;
  for (let i = 0; i < token.length; i++) {
    h ^= token.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

export function localEmbed(text: string): number[] {
  const vec = new Array(LOCAL_DIM).fill(0);
  const tokens = tokenize(text);
  for (const t of tokens) {
    const h = fnvHash(t);
    const idx = h % LOCAL_DIM;
    const sign = h & 1 ? 1 : -1;
    vec[idx] += sign;
  }
  return l2Normalize(vec);
}

function l2Normalize(vec: number[]): number[] {
  let sum = 0;
  for (const v of vec) sum += v * v;
  const norm = Math.sqrt(sum) || 1;
  return vec.map((v) => v / norm);
}

export function cosine(a: number[], b: number[]): number {
  const n = Math.min(a.length, b.length);
  let dot = 0;
  for (let i = 0; i < n; i++) dot += a[i] * b[i];
  return dot;
}

function weightedKeywordOverlap(query: string, doc: string): number {
  const qTokens = tokenize(query).filter(
    (t) => t.length > 1 && !STOPWORDS.has(t),
  );
  if (!qTokens.length) return 0;
  const docLower = doc.toLowerCase();
  let hit = 0;
  let total = 0;
  for (const t of qTokens) {
    const w = /^[a-z0-9_]+$/i.test(t) ? 2.5 : 1.0;
    total += w;
    if (docLower.includes(t)) hit += w;
  }
  return total === 0 ? 0 : hit / total;
}

async function apiEmbed(texts: string[]): Promise<number[][]> {
  const client = new OpenAI({
    baseURL: config.embeddingBaseUrl,
    apiKey: config.embeddingApiKey,
  });
  const res = await client.embeddings.create({
    model: config.embeddingModel,
    input: texts,
  });
  return res.data
    .sort((a, b) => a.index - b.index)
    .map((d) => d.embedding);
}

export async function embedTexts(texts: string[]): Promise<{
  mode: "api" | "local";
  vectors: number[][];
}> {
  if (useApiEmbedding()) {
    const vectors = await apiEmbed(texts);
    return { mode: "api", vectors };
  }
  return { mode: "local", vectors: texts.map(localEmbed) };
}

function walkMarkdownFiles(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  const out: string[] = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) {
      if (e.name === ".obsidian" || e.name === ".claude" || e.name === "node_modules") {
        continue;
      }
      out.push(...walkMarkdownFiles(full));
    } else if (e.isFile() && e.name.toLowerCase().endsWith(".md")) {
      if (e.name.toLowerCase() === "readme.md") continue;
      out.push(full);
    }
  }
  return out;
}

function chunkMarkdown(text: string): string[] {
  const normalized = text.replace(/\r\n/g, "\n").trim();
  if (!normalized) return [];
  const parts = normalized.split(/\n(?=#{1,3}\s)/);
  const chunks: string[] = [];
  for (const part of parts) {
    const trimmed = part.trim();
    if (!trimmed) continue;
    if (trimmed.length <= MAX_CHARS) {
      chunks.push(trimmed);
      continue;
    }
    for (let i = 0; i < trimmed.length; i += MAX_CHARS) {
      chunks.push(trimmed.slice(i, i + MAX_CHARS));
    }
  }
  return chunks.length ? chunks : [normalized];
}

export async function buildKnowledgeIndex(): Promise<KnowledgeIndex> {
  const root = config.knowledgeDir;
  const files = walkMarkdownFiles(root);
  const pending: Array<{ source: string; text: string; id: string }> = [];

  for (const file of files) {
    const rel = path.relative(root, file).split(path.sep).join("/");
    const content = fs.readFileSync(file, "utf8");
    const pieces = chunkMarkdown(content);
    pieces.forEach((text, i) => {
      pending.push({ source: rel, text, id: `${rel}#${i}` });
    });
  }

  const { mode, vectors } = await embedTexts(pending.map((p) => p.text));
  const chunks: KnowledgeChunk[] = pending.map((p, i) => ({
    id: p.id,
    source: p.source,
    text: p.text,
    embedding: vectors[i],
  }));

  const index: KnowledgeIndex = {
    version: 1,
    createdAt: new Date().toISOString(),
    embeddingMode: mode,
    chunks,
  };

  const outDir = path.dirname(config.knowledgeIndexPath);
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(config.knowledgeIndexPath, JSON.stringify(index), "utf8");
  return index;
}

export function loadKnowledgeIndex(): KnowledgeIndex | null {
  if (!fs.existsSync(config.knowledgeIndexPath)) return null;
  const raw = fs.readFileSync(config.knowledgeIndexPath, "utf8");
  return JSON.parse(raw) as KnowledgeIndex;
}

export async function retrieve(
  query: string,
  topK = 8,
): Promise<RetrievedChunk[]> {
  const index = loadKnowledgeIndex();
  if (!index || !index.chunks.length) return [];

  const { vectors } = await embedTexts([query]);
  const queryVec = vectors[0];

  const scored = index.chunks.map((c) => {
    const semantic = cosine(queryVec, c.embedding);
    const lexical = weightedKeywordOverlap(query, `${c.source}\n${c.text}`);
    const score = 0.5 * semantic + 0.5 * lexical;
    return {
      id: c.id,
      source: c.source,
      text: c.text,
      score,
    };
  });

  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, topK);
}
