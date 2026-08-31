"""Job search helpers: city codes + card normalization + salary filter."""

from __future__ import annotations

import re
from typing import Any

from resume_select import infer_job_track

# Subset of zhipin-geek CITY_CODES (extend as needed)
CITY_CODES: dict[str, str] = {
    "全国": "100010000",
    "北京": "101010100",
    "上海": "101020100",
    "广州": "101280100",
    "深圳": "101280600",
    "杭州": "101210100",
    "成都": "101270100",
    "南京": "101190100",
    "武汉": "101200100",
    "苏州": "101190400",
}

# Boss search salary band hint (20-30K). Real gate is client-side min_k.
SALARY_BAND_20_30 = "406"


def resolve_city(name: str) -> str:
    raw = (name or "").strip()
    if not raw:
        return CITY_CODES["上海"]
    if raw.isdigit() and len(raw) >= 6:
        return raw
    return CITY_CODES.get(raw, CITY_CODES.get("全国", "100010000"))


def parse_salary_monthly_k(salary_desc: str) -> tuple[float | None, float | None]:
    """Parse Boss salaryDesc into (low_k, high_k) monthly thousands.

    Returns (None, None) for 日薪/面议/unknown.
    """
    text = (salary_desc or "").strip().replace(" ", "")
    if not text:
        return None, None
    if "元/天" in text or "/天" in text or "日薪" in text:
        return None, None
    if "面议" in text:
        return None, None

    m = re.search(r"(\d+(?:\.\d+)?)\s*[Kk]以上", text)
    if m:
        v = float(m.group(1))
        return v, v

    m = re.search(
        r"(\d+(?:\.\d+)?)\s*[Kk]?\s*[-~～—]\s*(\d+(?:\.\d+)?)\s*[Kk]",
        text,
        re.I,
    )
    if m:
        return float(m.group(1)), float(m.group(2))

    m = re.search(r"(\d+(?:\.\d+)?)\s*[Kk](?![以上\d])", text)
    if m:
        v = float(m.group(1))
        return v, v

    return None, None


def meets_min_salary_k(salary_desc: str, *, min_k: float = 20.0) -> bool:
    """True iff monthly range lower bound >= min_k (default 20)."""
    low, _high = parse_salary_monthly_k(salary_desc)
    if low is None:
        return False
    return low >= min_k


def job_text_blob(job: dict[str, Any]) -> str:
    return " ".join(
        str(job.get(k) or "")
        for k in ("jobName", "brandName", "salaryDesc", "bossName", "cityName")
    )


def normalize_job_card(raw: dict[str, Any]) -> dict[str, Any]:
    job_name = str(raw.get("jobName") or raw.get("title") or "")
    brand = str(raw.get("brandName") or raw.get("brand") or raw.get("company") or "")
    salary = str(raw.get("salaryDesc") or raw.get("salary") or "")
    security_id = str(raw.get("securityId") or "")
    lid = str(raw.get("lid") or "")
    encrypt_job_id = str(raw.get("encryptJobId") or raw.get("jobId") or "")
    track = infer_job_track(job_name, brand, str(raw.get("skills") or ""))
    low_k, high_k = parse_salary_monthly_k(salary)
    return {
        "jobName": job_name,
        "brandName": brand,
        "salaryDesc": salary,
        "salaryLowK": low_k,
        "salaryHighK": high_k,
        "securityId": security_id,
        "lid": lid,
        "encryptJobId": encrypt_job_id,
        "jobTrack": track,
        "cityName": str(raw.get("cityName") or raw.get("city") or ""),
        "bossName": str(raw.get("bossName") or raw.get("boss") or ""),
        "raw": raw,
    }


def draft_greeting(job: dict[str, Any]) -> str:
    """Track-aware greeting template (no LLM)."""
    track = job.get("jobTrack") or "backend-agent"
    job_name = job.get("jobName") or "该岗位"
    brand = job.get("brandName") or "贵司"
    if track == "data-agent":
        return (
            f"您好，看到{brand}的「{job_name}」，我对实时数仓 / Flink 链路和数据智能"
            f"（治理 Agent、契约）方向比较匹配。方便的话我想了解下团队技术栈和当前重点，"
            f"也可以先发一份数据+AI 方向简历给您。"
        )
    return (
        f"您好，看到{brand}的「{job_name}」，我这边是 Java/Python 后端，"
        f"也在做 Agent / RAG 平台工程。方便聊聊团队方向和岗位侧重点吗？"
        f"需要的话我可以发后端+AI 方向简历。"
    )
