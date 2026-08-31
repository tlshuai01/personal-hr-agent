"""Write structured reports for manual review (C1 dry-run / C2 sent)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ReportEntry:
    index: int
    status: str  # dry_run | sent | send_fail | policy_blocked | agent_blocked | error
    session_id: str
    boss_name: str
    company: str
    job_title: str
    question: str
    answer: str = ""
    block_reason: str = ""
    sources: list[str] = field(default_factory=list)
    error: str = ""
    actions: list[dict[str, Any]] = field(default_factory=list)
    resume_already_sent: bool = False


class DryRunReport:
    def __init__(self, *, phase: str, limit: int, total_sessions: int, candidates: int) -> None:
        self.phase = phase
        self.limit = limit
        self.total_sessions = total_sessions
        self.candidates = candidates
        self.entries: list[ReportEntry] = []
        self._counter = 0

    def add(
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
        self._counter += 1
        self.entries.append(
            ReportEntry(
                index=self._counter,
                status=status,
                session_id=session_id,
                boss_name=str(friend.get("name") or "?"),
                company=str(friend.get("brandName") or "?"),
                job_title=str(friend.get("jobName") or friend.get("title") or "?"),
                question=question,
                answer=answer,
                block_reason=block_reason,
                sources=list(sources or []),
                error=error,
                actions=list(actions or []),
                resume_already_sent=resume_already_sent,
            )
        )

    def write_markdown(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).astimezone()
        lines = [
            "# Boss Bridge 对话记录",
            "",
            f"- **生成时间**：{now.strftime('%Y-%m-%d %H:%M %Z')}",
            f"- **阶段**：{self.phase}",
            f"- **处理上限**：{self.limit}",
            f"- **沟通列表**：{self.total_sessions} 会话，启发式需回复 {self.candidates}",
            f"- **本报告条数**：{len(self.entries)}",
            "",
            (
                "> 仅供 Owner 审阅回复质量。**未发送到 Boss**（C1 dry-run）。"
                if self.phase == "c1"
                else "> 含真实发送记录。请定期审阅质量并标注改进点。"
            ),
            "",
            "---",
            "",
        ]

        for e in self.entries:
            lines.extend(
                [
                    f"## {e.index}. {e.boss_name} @ {e.company}",
                    "",
                    f"| 项 | 内容 |",
                    f"|----|------|",
                    f"| 状态 | `{e.status}` |",
                    f"| 职位 | {e.job_title} |",
                    f"| sessionId | `{e.session_id}` |",
                    f"| 已发过简历 | {'是' if e.resume_already_sent else '否/未知'} |",
                    "",
                    "### HR 消息",
                    "",
                    "```",
                    e.question or "(空)",
                    "```",
                    "",
                ]
            )
            if e.status in ("dry_run", "sent", "send_fail"):
                title = "### Agent 拟回复" if e.status == "dry_run" else "### 我方回复"
                lines.extend([title, "", e.answer or "(空)", ""])
                if e.actions:
                    lines.append("**动作**：")
                    for act in e.actions:
                        if act.get("type") == "send_resume":
                            lines.append(
                                f"- 发送简历：`{act.get('label') or act.get('track')}`"
                            )
                        else:
                            lines.append(f"- `{act}`")
                    lines.append("")
                if e.sources:
                    lines.append("**检索来源**：")
                    for s in e.sources:
                        lines.append(f"- `{s}`")
                    lines.append("")
            elif e.block_reason:
                lines.extend(["### 拦截原因", "", e.block_reason, ""])
            if e.error:
                lines.extend(["### 错误", "", e.error, ""])
            lines.extend(["---", ""])

        lines.extend(
            [
                "## 审阅占位（请直接在本文件标注）",
                "",
                "| # | 问题 | 你的修正意见 |",
                "|---|------|-------------|",
            ]
        )
        for e in self.entries:
            if e.status in ("dry_run", "sent", "send_fail"):
                lines.append(f"| {e.index} | | |")

        path.write_text("\n".join(lines), encoding="utf-8")
