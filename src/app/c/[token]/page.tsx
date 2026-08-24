"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ChatPanel } from "@/components/ChatPanel";

type Meta = {
  label: string;
  expiresAt: string;
  maxMessages: number | null;
  messageCount: number;
};

export default function GuestChatPage() {
  const params = useParams<{ token: string }>();
  const token = params?.token ?? "";
  const [meta, setMeta] = useState<Meta | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/share/${encodeURIComponent(token)}`, {
          cache: "no-store",
        });
        const data = await res.json();
        if (cancelled) return;
        if (!res.ok || !data.ok) {
          setError(data.message || "分享链接无效");
          setMeta(null);
        } else {
          setMeta({
            label: data.label,
            expiresAt: data.expiresAt,
            maxMessages: data.maxMessages,
            messageCount: data.messageCount,
          });
        }
      } catch {
        if (!cancelled) setError("验证分享链接失败，请稍后重试");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <main className="container" style={{ padding: "2rem 0 3rem" }}>
      <p className="badge">Guest Chat</p>
      <h1 style={{ marginBottom: "0.4rem" }}>与候选人对话</h1>
      {loading && <p className="muted">正在验证分享链接…</p>}
      {!loading && error && (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>链接不可用</h2>
          <p className="muted">{error}</p>
        </div>
      )}
      {!loading && meta && (
        <>
          <p className="muted" style={{ marginBottom: "1rem" }}>
            {meta.label} · 已用 {meta.messageCount}
            {meta.maxMessages != null ? ` / ${meta.maxMessages}` : ""} 条消息 · 过期{" "}
            {new Date(meta.expiresAt).toLocaleString()}
          </p>
          <ChatPanel token={token} />
        </>
      )}
    </main>
  );
}
