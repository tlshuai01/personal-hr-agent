import OpenAI from "openai";
import { completeChat } from "@/lib/llm";
import {
  type ChatChannel,
  type ResumeTrack,
  formatRetrievedContext,
  getSystemPrompt,
  inferResumeTrack,
  resumeTrackLabel,
  sanitizeCandidateReply,
  shouldOfferResume,
} from "@/lib/prompt";
import { retrieve } from "@/lib/rag";

export type ChatTurn = { role: "user" | "assistant"; content: string };

export type ReplyMeta = {
  bossName?: string;
  company?: string;
  jobTitle?: string;
  /** Boss 会话历史里已出现附件简历交换 */
  resumeAlreadySent?: boolean;
};

export type ReplyAction = {
  type: "send_resume";
  track: ResumeTrack;
  label: string;
};

const SENSITIVE_PATTERNS: Array<{ re: RegExp; reason: string }> = [
  { re: /微信|手机号|电话|联系方式|vx/i, reason: "联系方式不宜自动交换" },
  { re: /身份证|银行卡|住址/i, reason: "隐私信息不宜自动回复" },
];

export function detectSensitiveUserMessage(text: string): string | null {
  for (const p of SENSITIVE_PATTERNS) {
    if (p.re.test(text)) return p.reason;
  }
  return null;
}

export type GenerateReplyResult = {
  reply: string;
  blocked: boolean;
  blockReason?: string;
  sources: string[];
  actions: ReplyAction[];
};

export type GenerateReplyOptions = {
  channel?: ChatChannel;
  meta?: ReplyMeta;
};

export async function generateReply(
  messages: ChatTurn[],
  options: GenerateReplyOptions = {},
): Promise<GenerateReplyResult> {
  const channel: ChatChannel = options.channel ?? "share";
  const lastUser = [...messages].reverse().find((m) => m.role === "user");
  if (!lastUser) {
    return {
      reply: "",
      blocked: true,
      blockReason: "缺少用户消息",
      sources: [],
      actions: [],
    };
  }

  const sensitive = detectSensitiveUserMessage(lastUser.content);
  if (sensitive) {
    return {
      reply: "",
      blocked: true,
      blockReason: sensitive,
      sources: [],
      actions: [],
    };
  }

  const retrieved = await retrieve(lastUser.content, 8);
  const context = formatRetrievedContext(retrieved);
  const sources = [...new Set(retrieved.map((r) => r.source))];

  const resumeAlreadySent = Boolean(options.meta?.resumeAlreadySent);
  let metaHint = "";
  if (channel === "boss" && options.meta) {
    metaHint =
      `【会话上下文】招聘方：${options.meta.bossName || "?"}；公司：${options.meta.company || "?"}；职位：${options.meta.jobTitle || "?"}。` +
      (resumeAlreadySent
        ? "本会话【已发送过附件简历】，回复中禁止再提发送/附上简历，只回答当前问题。"
        : "本会话尚未标记已发简历；是否推简历按知识库 Boss 口径。");
  }

  const llmMessages: OpenAI.Chat.ChatCompletionMessageParam[] = [
    { role: "system", content: getSystemPrompt(channel) },
    { role: "system", content: context },
    ...(metaHint
      ? [{ role: "system" as const, content: metaHint }]
      : []),
    ...messages.map((m) => ({
      role: m.role as "user" | "assistant",
      content: m.content,
    })),
  ];

  const raw = await completeChat(llmMessages, 0.25);
  let reply = sanitizeCandidateReply(raw);
  if (resumeAlreadySent) {
    reply = reply
      .replace(/这是我的简历[，,。]?[^\n]{0,40}/g, "")
      .replace(/请您先看下[，,。]?/g, "")
      .replace(/方便发(?:一下)?简历[^\n]{0,20}/g, "")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  const actions: ReplyAction[] = [];
  if (
    channel === "boss" &&
    !resumeAlreadySent &&
    shouldOfferResume(lastUser.content)
  ) {
    const track = inferResumeTrack(options.meta?.jobTitle, lastUser.content);
    actions.push({
      type: "send_resume",
      track,
      label: resumeTrackLabel(track),
    });
  }

  return { reply, blocked: false, sources, actions };
}
