"""Append-only audit log for Owner review of Boss reply quality."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLog:
    """Daily markdown + JSONL under reports/audit/ for periodic quality review."""

    def __init__(self, root: Path, *, phase: str = "c2") -> None:
        self.phase = phase
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        day = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
        self.md_path = self.root / f"{phase}-{day}.md"
        self.jsonl_path = self.root / f"{phase}-{day}.jsonl"
        if not self.md_path.exists():
            now = datetime.now(timezone.utc).astimezone()
            self.md_path.write_text(
                "\n".join(
                    [
                        f"# Boss Bridge {phase.upper()} 审计日志",
                        "",
                        f"- **日期**：{day}",
                        f"- **阶段**：{phase}（真实发送到 Boss，请定期审阅质量）",
                        f"- **开始**：{now.strftime('%H:%M %Z')}",
                        "",
                        "> 在每条下方的「审阅」行填写问题与期望改法。",
                        "",
                        "---",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

    def record(
        self,
        *,
        status: str,
        friend: dict[str, Any],
        session_id: str,
        question: str = "",
        answer: str = "",
        block_reason: str = "",
        sources: list[str] | None = None,
        error: str = "",
        actions: list[dict[str, Any]] | None = None,
        resume_already_sent: bool = False,
    ) -> None:
        now = datetime.now(timezone.utc).astimezone()
        boss = str(friend.get("name") or "?")
        company = str(friend.get("brandName") or "?")
        job = str(friend.get("jobName") or friend.get("title") or "?")
        sources = list(sources or [])
        actions = list(actions or [])

        row = {
            "ts": now.isoformat(timespec="seconds"),
            "phase": self.phase,
            "status": status,
            "sessionId": session_id,
            "bossName": boss,
            "company": company,
            "jobTitle": job,
            "question": question,
            "answer": answer,
            "blockReason": block_reason,
            "sources": sources,
            "error": error,
            "actions": actions,
            "resumeAlreadySent": resume_already_sent,
        }
        with self.jsonl_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

        lines = [
            f"## {now.strftime('%H:%M:%S')} · {boss} @ {company}",
            "",
            f"| 项 | 内容 |",
            f"|----|------|",
            f"| 状态 | `{status}` |",
            f"| 职位 | {job} |",
            f"| sessionId | `{session_id}` |",
            f"| 已发过简历 | {'是' if resume_already_sent else '否/未知'} |",
            "",
            "### 对方消息",
            "",
            "```",
            question or "(空)",
            "```",
            "",
        ]
        if answer:
            lines.extend(["### 我方回复（已发送或拟发送）", "", answer, ""])
        if actions:
            lines.append("**动作**：")
            for act in actions:
                lines.append(f"- `{act}`")
            lines.append("")
        if sources:
            lines.append("**检索来源**：")
            for s in sources:
                lines.append(f"- `{s}`")
            lines.append("")
        if block_reason:
            lines.extend(["### 拦截", "", block_reason, ""])
        if error:
            lines.extend(["### 错误", "", error, ""])
        lines.extend(
            [
                "**审阅**：问题：____　期望改法：____",
                "",
                "---",
                "",
            ]
        )
        with self.md_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines))
