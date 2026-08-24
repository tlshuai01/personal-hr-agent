import OpenAI from "openai";
import { config } from "./config";

export function getLlmClient(): OpenAI {
  return new OpenAI({
    baseURL: config.llmBaseUrl,
    apiKey: config.llmApiKey,
  });
}

export async function streamChatCompletion(
  messages: OpenAI.Chat.ChatCompletionMessageParam[],
  temperature = 0.3,
): Promise<ReadableStream<Uint8Array>> {
  const client = getLlmClient();
  const stream = await client.chat.completions.create({
    model: config.llmModel,
    messages,
    temperature,
    stream: true,
  });

  const encoder = new TextEncoder();
  return new ReadableStream({
    async start(controller) {
      try {
        for await (const chunk of stream) {
          const text = chunk.choices[0]?.delta?.content ?? "";
          if (text) controller.enqueue(encoder.encode(text));
        }
        controller.close();
      } catch (err) {
        controller.error(err);
      }
    },
  });
}

export async function completeChat(
  messages: OpenAI.Chat.ChatCompletionMessageParam[],
  temperature = 0.2,
): Promise<string> {
  const client = getLlmClient();
  const res = await client.chat.completions.create({
    model: config.llmModel,
    messages,
    temperature,
    stream: false,
  });
  return res.choices[0]?.message?.content ?? "";
}
