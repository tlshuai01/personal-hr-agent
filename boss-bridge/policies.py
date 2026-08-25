"""Reply policies — bridge-side guardrails."""

from __future__ import annotations

import re
from dataclasses import dataclass

SENSITIVE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"薪资|工资|年薪|月薪|多少钱|期望.*薪", re.I), "薪资话题需真人沟通"),
    (re.compile(r"offer|录用|入职时间|什么时候能到岗", re.I), "录用承诺需真人沟通"),
    (re.compile(r"微信|手机号|电话|联系方式|vx", re.I), "联系方式不宜自动交换"),
    (re.compile(r"身份证|银行卡|住址", re.I), "隐私信息不宜自动回复"),
]


@dataclass
class PolicyResult:
    allowed: bool
    reason: str = ""


def should_auto_reply(message: str, *, phase: str = "c1") -> PolicyResult:
    text = (message or "").strip()
    if not text:
        return PolicyResult(False, "空消息")

    for pattern, reason in SENSITIVE_PATTERNS:
        if pattern.search(text):
            return PolicyResult(False, reason)

    if len(text) > 2000:
        return PolicyResult(False, "消息过长")

    # C1 always allows (dry-run logs only); C2/C3 same keyword gate
    _ = phase
    return PolicyResult(True)
