"use client";

import { FormEvent, useState } from "react";

type LinkRow = {
  token: string;
  label: string;
  url: string;
  status: string;
  expires_at: string;
  max_messages: number | null;
  message_count: number;
};

export default function AdminPage() {
  const [password, setPassword] = useState("");
  const [authed, setAuthed] = useState(false);
  const [links, setLinks] = useState<LinkRow[]>([]);
  const [label, setLabel] = useState("");
  const [expiresInHours, setExpiresInHours] = useState(72);
  const [maxMessages, setMaxMessages] = useState(100);
  const [createdUrl, setCreatedUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadLinks(pwd = password) {
    const res = await fetch("/api/share", {
      headers: { "x-owner-password": pwd },
      cache: "no-store",
    });
    if (!res.ok) throw new Error("密码错误或加载失败");
    const data = await res.json();
    setLinks(data.links);
  }

  async function onLogin(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await loadLinks();
      setAuthed(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
    }
  }

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setCreatedUrl(null);
    const res = await fetch("/api/share", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-owner-password": password,
      },
      body: JSON.stringify({
        label: label || "HR 分享",
        expiresInHours,
        maxMessages,
      }),
    });
    if (!res.ok) {
      setError("创建失败");
      return;
    }
    const data = await res.json();
    setCreatedUrl(data.link.url);
    setLabel("");
    await loadLinks();
  }

  async function onRevoke(token: string) {
    if (!confirm("确认作废该链接？")) return;
    await fetch("/api/share", {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
        "x-owner-password": password,
      },
      body: JSON.stringify({ token }),
    });
    await loadLinks();
  }

  if (!authed) {
    return (
      <main className="container" style={{ padding: "3rem 0" }}>
        <h1>Owner 管理台</h1>
        <form className="card" onSubmit={onLogin} style={{ display: "grid", gap: "0.8rem", maxWidth: 420 }}>
          <label>
            管理密码
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={{ marginTop: 6 }}
            />
          </label>
          {error && <div style={{ color: "var(--danger)" }}>{error}</div>}
          <button className="btn" type="submit">
            登录
          </button>
        </form>
      </main>
    );
  }

  return (
    <main className="container" style={{ padding: "2.5rem 0 4rem" }}>
      <h1>Owner 管理台</h1>
      <p className="muted">创建限时分享链接给 HR。密码仅保存在本页内存。</p>

      <form className="card" onSubmit={onCreate} style={{ display: "grid", gap: "0.8rem", marginBottom: "1.2rem" }}>
        <h2 style={{ margin: 0 }}>创建分享链接</h2>
        <label>
          标签
          <input className="input" value={label} onChange={(e) => setLabel(e.target.value)} placeholder="某公司 HR" style={{ marginTop: 6 }} />
        </label>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.8rem" }}>
          <label>
            有效小时
            <input
              className="input"
              type="number"
              value={expiresInHours}
              onChange={(e) => setExpiresInHours(Number(e.target.value))}
              style={{ marginTop: 6 }}
            />
          </label>
          <label>
            最大消息数
            <input
              className="input"
              type="number"
              value={maxMessages}
              onChange={(e) => setMaxMessages(Number(e.target.value))}
              style={{ marginTop: 6 }}
            />
          </label>
        </div>
        {error && <div style={{ color: "var(--danger)" }}>{error}</div>}
        {createdUrl && (
          <div className="badge" style={{ wordBreak: "break-all", padding: "0.6rem 0.8rem" }}>
            已创建：{createdUrl}
          </div>
        )}
        <button className="btn" type="submit">
          创建链接
        </button>
      </form>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>链接列表</h2>
        <div style={{ display: "grid", gap: "0.8rem" }}>
          {links.map((l) => (
            <div
              key={l.token}
              style={{
                borderTop: "1px solid var(--line)",
                paddingTop: "0.8rem",
                display: "grid",
                gap: "0.35rem",
              }}
            >
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
                <strong>{l.label}</strong>
                <span
                  className={
                    l.status === "active"
                      ? "badge"
                      : l.status === "expired" || l.status === "limit_reached"
                        ? "badge warn"
                        : "badge bad"
                  }
                >
                  {l.status}
                </span>
              </div>
              <div className="muted" style={{ wordBreak: "break-all", fontSize: "0.9rem" }}>
                {l.url}
              </div>
              <div className="muted" style={{ fontSize: "0.85rem" }}>
                用量 {l.message_count}
                {l.max_messages != null ? ` / ${l.max_messages}` : ""} · 过期{" "}
                {new Date(l.expires_at).toLocaleString()}
              </div>
              {l.status === "active" && (
                <div>
                  <button className="btn danger" type="button" onClick={() => onRevoke(l.token)}>
                    作废
                  </button>
                </div>
              )}
            </div>
          ))}
          {!links.length && <p className="muted">暂无链接</p>}
        </div>
      </div>
    </main>
  );
}
