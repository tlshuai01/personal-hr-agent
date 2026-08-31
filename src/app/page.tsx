import Link from "next/link";

export default function HomePage() {
  return (
    <main className="container" style={{ padding: "3rem 0 4rem" }}>
      <p className="badge">Personal Job Agent</p>
      <h1 style={{ fontSize: "clamp(2rem, 4vw, 2.8rem)", margin: "0.8rem 0" }}>
        个人求职 Agent
      </h1>
      <p className="muted" style={{ maxWidth: 560, lineHeight: 1.7 }}>
        维护个人知识库，生成限时分享链接；也可经 Boss 渠道自动回复。招聘方与你对话时，回答以知识库为准，无依据不编造。
      </p>
      <div style={{ display: "flex", gap: "0.75rem", marginTop: "1.5rem" }}>
        <Link className="btn" href="/admin">
          进入管理台
        </Link>
        <Link className="btn secondary" href="/api/health">
          健康检查
        </Link>
      </div>
      <div className="card" style={{ marginTop: "2rem" }}>
        <h2 style={{ marginTop: 0 }}>使用方式</h2>
        <ol className="muted" style={{ lineHeight: 1.8 }}>
          <li>在 knowledge 目录维护 Markdown 事实源并执行 npm run knowledge:index</li>
          <li>在管理台创建限时分享链接</li>
          <li>把 /c/&lt;token&gt; 发给对方开始对话；或启动 boss-bridge C1/C2</li>
        </ol>
        <p className="muted" style={{ marginBottom: 0 }}>
          首页不提供聊天入口，必须经分享链接或渠道 Bridge 访问。
        </p>
      </div>
    </main>
  );
}
