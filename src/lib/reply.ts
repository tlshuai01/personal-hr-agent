import OpenAI from "openai";
import { completeChat } from "@/lib/llm";
import { formatRetrievedContext, SYSTEM_PROMPT } from "@/lib/prompt";
import { retrieve } from "@/lib/rag";

export type ChatTurn = { role: "user" | "assistant"; content: string };

const SENSITIVE_PATTERNS: Array<{ re: RegExp; reason: string }> = [
  { re: /薪资|工资|年薪|月薪|多少钱|期望.*薪/i, reason: "薪资话题需真人沟通" },
  { re: /offer|录用|入职时间|什么时候能到岗/i, reason: "录用承诺需真人沟通" },
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
};

export async function generateReply(
  messages: ChatTurn[],
): Promise<GenerateReplyResult> {
  const lastUser = [...messages].reverse().find((m) => m.role === "user");
  if (!lastUser) {
    return {
      reply: "",
      blocked: true,
      blockReason: "缺少用户消息",
      sources: [],
    };
  }

  const sensitive = detectSensitiveUserMessage(lastUser.content);
  if (sensitive) {
    return {
      reply: "",
      blocked: true,
      blockReason: sensitive,
      sources: [],
    };
  }

  const retrieved = await retrieve(lastUser.content, 8);
  const context = formatRetrievedContext(retrieved);
  const sources = [...new Set(retrieved.map((r) => r.source))];

  const llmMessages: OpenAI.Chat.ChatCompletionMessageParam[] = [
    { role: "system", content: SYSTEM_PROMPT },
    { role: "system", content: context },
    ...messages.map((m) => ({
      role: m.role as "user" | "assistant",
      content: m.content,
    })),
  ];

  const reply = await completeChat(llmMessages, 0.25);
  return { reply: reply.trim(), blocked: false, sources };
}
