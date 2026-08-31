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
  // 智谱 embedding-3：单请求最多 64 条
  const batchSize = 64;
  const out: number[][] = new Array(texts.length);
  for (let i = 0; i < texts.length; i += batchSize) {
    const slice = texts.slice(i, i + batchSize);
    const res = await client.embeddings.create({
      model: config.embeddingModel,
      input: slice,
    });
    const sorted = res.data.sort((a, b) => a.index - b.index);
    sorted.forEach((d, j) => {
      out[i + j] = d.embedding;
    });
  }
  return out;
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
    let score = 0.5 * semantic + 0.5 * lexical;
    // 政策/基本信息：薪资、到岗、Boss 口径等优先露出（local hash 语义弱时更关键）
    if (shouldPinPolicy(query) && isPolicySource(c.source)) {
      score += 0.35;
    }
    score += topicPinBoost(query, c.source, c.text);
    return {
      id: c.id,
      source: c.source,
      text: c.text,
      score,
    };
  });

  scored.sort((a, b) => b.score - a.score);
  const top = scored.slice(0, Math.max(topK, 10));
  return ensureTopicChunks(query, top, scored, topK);
}

const POLICY_SOURCE_PREFIXES = [
  "01-基本信息/",
  "05-技能与问答/boundaries.md",
  "05-技能与问答/boss-channel.md",
  "05-技能与问答/faq.md",
];

function isPolicySource(source: string): boolean {
  return POLICY_SOURCE_PREFIXES.some(
    (p) => source === p || source.startsWith(p),
  );
}

/** 问到求职政策类话题时，抬高基本信息 / Boss 口径文档权重 */
function shouldPinPolicy(query: string): boolean {
  return /薪|期望|总包|预算|给不到|到岗|入职|简历|微信|电话|外包|驻场|合适|远程|加班|日语|日英|英语|双语|外语|语言|全日制|统招|学历|本科|硕士|沟通怎么样|离职|现薪|感兴趣|聊聊/.test(
    query,
  );
}

/**
 * 专题强 pin：避免「日英」不匹配「日语」正则、或开场只捞到 availability/compensation。
 */
function topicPinBoost(query: string, source: string, text: string): number {
  let boost = 0;
  const langQ = /日语|日英|英语|双语|外语|语言能力|沟通怎么样/.test(query);
  if (langQ) {
    if (source.includes("identity.md") && /日语|英语|外语|双语|无基础/.test(text)) {
      boost += 0.55;
    }
    if (source.includes("boss-channel.md") && /日语|英语|外语/.test(text)) {
      boost += 0.35;
    }
    if (source.includes("boundaries.md") && /外语|日语/.test(text)) {
      boost += 0.3;
    }
  }
  if (
    /薪|期望|总包|预算|给不到|现薪|到岗|离职|学历|统招/.test(query) &&
    source.includes("boss-quick-facts.md")
  ) {
    boost += 0.9;
  }
  if (
    /学历|全日制|统招|本科|硕士/.test(query) &&
    source.includes("education.md")
  ) {
    boost += 0.7;
  }
  if (/到岗|入职|多久.*到|需要多久/.test(query) && source.includes("availability.md")) {
    boost += 0.55;
  }
  if (
    /离职|为什么.*走|上家|看机会/.test(query) &&
    source.includes("leaving-narrative.md")
  ) {
    boost += 0.7;
  }
  if (
    /简历|感兴趣|聊聊|方便发|发简历|看看.*机会|打招呼/.test(query) &&
    source.includes("boss-channel.md")
  ) {
    boost += 0.4;
  }
  if (
    /简历|感兴趣|聊聊|方便发|发简历/.test(query) &&
    (source.includes("profile-summary.md") || source.includes("identity.md")) &&
    /Java|Python|定位|自我介绍/.test(text)
  ) {
    boost += 0.25;
  }
  return boost;
}

/** 清单式多问时，强制塞入关键政策文档（避免只被 availability 占满 topK） */
function ensureTopicChunks(
  query: string,
  ranked: RetrievedChunk[],
  allSorted: RetrievedChunk[],
  topK: number,
): RetrievedChunk[] {
  const rules: Array<{ re: RegExp; needle: string }> = [
    {
      re: /薪|期望|总包|现薪|预算|给不到|到岗|入职|离职|学历|统招|全日制|日语|日英|简历|感兴趣|聊聊/,
      needle: "boss-quick-facts.md",
    },
    { re: /薪|期望|总包|现薪|预算|给不到/, needle: "compensation.md" },
    { re: /学历|全日制|统招|本科|硕士/, needle: "education.md" },
    { re: /到岗|入职|需要多久/, needle: "availability.md" },
    { re: /离职|上家|为什么.*走|看机会|是否离职|在职/, needle: "leaving-narrative.md" },
    { re: /离职|在哪个城市|现居|base|在职|是否离职/, needle: "identity.md" },
    { re: /日语|日英|双语|外语|英语/, needle: "identity.md" },
    { re: /简历|感兴趣|聊聊|方便发/, needle: "boss-channel.md" },
  ];
  const out = ranked.slice(0, topK);
  const has = (needle: string) => out.some((c) => c.source.includes(needle));
  for (const rule of rules) {
    if (!rule.re.test(query) || has(rule.needle)) continue;
    const cand = allSorted.find((c) => c.source.includes(rule.needle));
    if (!cand) continue;
    if (out.length >= topK) out.pop();
    out.unshift(cand);
  }
  return out.slice(0, topK);
}
