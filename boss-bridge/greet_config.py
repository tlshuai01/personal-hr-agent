"""Load greet/search policy from greet_config.json."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path
from typing import Any

_DEFAULT_PATH = Path(__file__).resolve().parent / "greet_config.json"


@dataclass
class GreetConfig:
    enabled: bool = True
    city: str = "上海"
    queries: list[str] = field(default_factory=lambda: ["Java Agent"])
    count_per_query: int = 5
    max_pages: int = 3
    min_salary_k: float = 20.0
    skip_keywords: list[str] = field(default_factory=lambda: ["日结", "实习"])
    active_start: time = field(default_factory=lambda: time(9, 0))
    active_end: time = field(default_factory=lambda: time(18, 0))
    greet_delay_sec: float = 1.5
    loop_interval_sec: int = 1800
    reply_signature: str = "[本条消息由个人求职 Agent 发送]"
    path: Path = field(default_factory=lambda: _DEFAULT_PATH)


def _parse_hhmm(raw: str, default: time) -> time:
    text = (raw or "").strip()
    if not text:
        return default
    try:
        hh, mm = text.split(":", 1)
        return time(int(hh), int(mm))
    except (TypeError, ValueError):
        return default


def load_greet_config(path: Path | None = None) -> GreetConfig:
    p = path or _DEFAULT_PATH
    data: dict[str, Any] = {}
    if p.exists():
        try:
            loaded = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except (json.JSONDecodeError, OSError):
            data = {}

    hours = data.get("active_hours") if isinstance(data.get("active_hours"), dict) else {}
    queries = data.get("queries")
    if not isinstance(queries, list) or not queries:
        queries = ["Java Agent"]
    skips = data.get("skip_keywords")
    if not isinstance(skips, list):
        skips = ["日结", "实习"]

    return GreetConfig(
        enabled=bool(data.get("enabled", True)),
        city=str(data.get("city") or "上海"),
        queries=[str(q).strip() for q in queries if str(q).strip()],
        count_per_query=int(data.get("count_per_query") or 5),
        max_pages=int(data.get("max_pages") or 3),
        min_salary_k=float(data.get("min_salary_k") or 20),
        skip_keywords=[str(s) for s in skips if str(s).strip()],
        active_start=_parse_hhmm(str(hours.get("start") or "09:00"), time(9, 0)),
        active_end=_parse_hhmm(str(hours.get("end") or "18:00"), time(18, 0)),
        greet_delay_sec=float(data.get("greet_delay_sec") or 1.5),
        loop_interval_sec=int(data.get("loop_interval_sec") or 1800),
        reply_signature=str(
            data.get("reply_signature") or "[本条消息由个人求职 Agent 发送]"
        ),
        path=p,
    )


def is_within_active_hours(cfg: GreetConfig, now: datetime | None = None) -> bool:
    current = (now or datetime.now()).time()
    start, end = cfg.active_start, cfg.active_end
    if start <= end:
        return start <= current < end
    # overnight window (e.g. 22:00-06:00)
    return current >= start or current < end


def contains_skip_keyword(text: str, keywords: list[str]) -> str | None:
    blob = text or ""
    for kw in keywords:
        if kw and kw in blob:
            return kw
    return None
