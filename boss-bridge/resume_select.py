"""Select Boss attachment resume by JD track + language."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_CATALOG_PATH = Path(__file__).resolve().parent / "resume_catalog.json"

DATA_HINTS = (
    "数据",
    "flink",
    "大数据",
    "数仓",
    "特征",
    "etl",
    "实时计算",
    "data",
    "mdm",
    "血缘",
    "数据治理",
    "数据中台",
    "数据开发",
    "数据平台",
)

# Explicit English resume request only (not "外企" / English job title alone)
ENGLISH_RESUME_HINTS = (
    r"英文简历",
    r"英语简历",
    r"英文版简历",
    r"english\s*resume",
    r"resume\s*in\s*english",
    r"发.*英文",
    r"要.*英文.*简历",
    r"英文的",
)


@dataclass(frozen=True)
class ResumeAttachment:
    resume_id: str
    name: str
    track: str
    lang: str


def load_catalog(path: Path | None = None) -> list[ResumeAttachment]:
    p = path or _CATALOG_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    out: list[ResumeAttachment] = []
    for row in data.get("attachments") or []:
        if not isinstance(row, dict):
            continue
        rid = str(row.get("resumeId") or "").strip()
        if not rid:
            continue
        out.append(
            ResumeAttachment(
                resume_id=rid,
                name=str(row.get("name") or ""),
                track=str(row.get("track") or "backend-agent"),
                lang=str(row.get("lang") or "zh"),
            )
        )
    return out


def infer_job_track(*texts: str | None) -> str:
    blob = " ".join(t for t in texts if t).lower()
    if any(h.lower() in blob or h in blob for h in DATA_HINTS):
        return "data-agent"
    return "backend-agent"


def wants_english_resume(*texts: str | None) -> bool:
    blob = " ".join(t for t in texts if t)
    if not blob.strip():
        return False
    return any(re.search(p, blob, flags=re.I) for p in ENGLISH_RESUME_HINTS)


def resolve_attachment(
    *,
    track: str,
    english: bool,
    catalog: list[ResumeAttachment] | None = None,
) -> ResumeAttachment:
    """Pick attachment: same track + lang; fallback zh on track; then any zh."""
    items = catalog if catalog is not None else load_catalog()
    if not items:
        raise ValueError("resume_catalog.json is empty")

    lang = "en" if english else "zh"
    for pref in (
        lambda a: a.track == track and a.lang == lang,
        # English requested but no EN for this track → still prefer any EN
        lambda a: english and a.lang == "en",
        # Normal / EN missing → Chinese on track
        lambda a: a.track == track and a.lang == "zh",
        lambda a: a.lang == "zh",
        lambda a: True,
    ):
        hit = next((a for a in items if pref(a)), None)
        if hit:
            return hit
    return items[0]


def resolve_for_friend(
    friend: dict[str, Any],
    *,
    user_text: str | None = None,
    track: str | None = None,
    catalog: list[ResumeAttachment] | None = None,
) -> ResumeAttachment:
    job_bits = [
        friend.get("jobName"),
        friend.get("title"),
        friend.get("sourceTitle"),
    ]
    inferred = track or infer_job_track(*job_bits, user_text)
    english = wants_english_resume(user_text)
    return resolve_attachment(track=inferred, english=english, catalog=catalog)
