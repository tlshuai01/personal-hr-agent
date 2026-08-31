"use client";

import { FormEvent, useState } from "react";

type Msg = { role: "user" | "assistant"; content: string };

const WELCOME =
  "你好，我是候选人的个人求职 Agent。可以问我经历、项目、技术栈或求职意向。回答基于知识库；关键录用以真人沟通为准。";

export function ChatPanel({ token }: { token: string }) {
  const [messages, setMessages] = useState<Msg[]>([
    { role: "assistant", content: WELCOME },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || busy) return;

    setError(null);
    setInput("");
    const next: Msg[] = [...messages, { role: "user", content: text }];
    setMessages(next);
    setBusy(true);

    const apiMessages = next.filter(
      (m, i) => !(i === 0 && m.role === "assistant" && m.content === WELCOME),
    );

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, messages: apiMessages }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.message || data.error || `请求失败 ${res.status}`);
      }

      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);
      const reader = res.body?.getReader();
      if (!reader) throw new Error("无流式响应");

      const decoder = new TextDecoder();
      let full = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        full += decoder.decode(value, { stream: true });
        const snapshot = full;
        setMessages((prev) => {
          const copy = [...prev];
          copy[copy.length - 1] = { role: "assistant", content: snapshot };
          return copy;
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "发送失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card" style={{ display: "grid", gap: "1rem" }}>
      <div
        style={{
          minHeight: 360,
          maxHeight: "60vh",
          overflow: "auto",
          display: "grid",
          gap: "0.75rem",
        }}
      >
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              justifySelf: m.role === "user" ? "end" : "start",
              maxWidth: "85%",
              padding: "0.75rem 0.9rem",
              borderRadius: 12,
              background: m.role === "user" ? "var(--brand-soft)" : "#fff",
              border: "1px solid var(--line)",
              whiteSpace: "pre-wrap",
              lineHeight: 1.55,
            }}
          >
            {m.content || (busy ? "…" : "")}
          </div>
        ))}
      </div>

      {error && (
        <div className="muted" style={{ color: "var(--danger)" }}>
          {error}
        </div>
      )}

      <form onSubmit={onSubmit} style={{ display: "flex", gap: "0.6rem" }}>
        <input
          className="input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="例如：介绍一下你做过的 RAG / Agent 项目"
          disabled={busy}
        />
        <button className="btn" type="submit" disabled={busy || !input.trim()}>
          发送
        </button>
      </form>

      <p className="muted" style={{ margin: 0, fontSize: "0.85rem" }}>
        回答基于候选人知识库检索；关键录用与谈判以真人沟通为准。
      </p>
    </div>
  );
}
