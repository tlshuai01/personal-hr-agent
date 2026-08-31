#!/usr/bin/env python3
"""Search Boss jobs and optionally greet (default: dry-run).

Config: boss-bridge/greet_config.json（时段 / 薪资 / 跳过词 / 关键词列表）

Examples:
  python scripts/search_and_greet.py
  python scripts/search_and_greet.py --force
  python scripts/search_and_greet.py --loop --force
  python scripts/search_and_greet.py "Java Agent" --city 上海 -n 5
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

_BRIDGE = Path(__file__).resolve().parents[1]
if str(_BRIDGE) not in sys.path:
    sys.path.insert(0, str(_BRIDGE))

from audit_log import AuditLog
from boss_transport import BossTransport, BossTransportError
from config import load_config
from greet_config import (
    GreetConfig,
    contains_skip_keyword,
    is_within_active_hours,
    load_greet_config,
)
from greet_store import GreetStore
from job_search import draft_greeting, job_text_blob, meets_min_salary_k, resolve_city

LOG = logging.getLogger("search-and-greet")


def _run_one_query(
    *,
    query: str,
    city: str,
    count: int,
    max_pages: int,
    min_salary_k: float,
    skip_keywords: list[str],
    force: bool,
    include_greeted: bool,
    enable_greet: bool,
    greet_delay: float,
    transport: BossTransport,
    store: GreetStore,
    audit: AuditLog,
) -> int:
    city_code = resolve_city(city)
    LOG.info(
        "search query=%r city=%s(%s) n=%d min_salary_k=%.0f force=%s",
        query,
        city,
        city_code,
        count,
        min_salary_k,
        force,
    )

    jobs: list[dict] = []
    seen_sid: set[str] = set()
    try:
        for page in range(1, max(1, max_pages) + 1):
            try:
                batch = transport.search_jobs(
                    query,
                    city=city_code,
                    page=page,
                    page_size=15,
                )
            except BossTransportError as exc:
                if jobs:
                    LOG.warning(
                        "search page %d failed (%s); use %d already fetched",
                        page,
                        exc,
                        len(jobs),
                    )
                    break
                raise
            if not batch:
                break
            for job in batch:
                sid = str(job.get("securityId") or "")
                if sid and sid not in seen_sid:
                    seen_sid.add(sid)
                    jobs.append(job)
            if len(jobs) >= count * 4:
                break
    except BossTransportError as exc:
        LOG.error("search failed: %s", exc)
        return 0

    if not jobs:
        LOG.warning("no jobs found for %r", query)
        return 0

    targets: list[dict] = []
    skipped_salary = 0
    skipped_kw = 0
    for job in jobs:
        sid = job.get("securityId") or ""
        if not sid:
            continue
        blob = job_text_blob(job)
        hit = contains_skip_keyword(blob, skip_keywords)
        if hit:
            skipped_kw += 1
            LOG.info(
                "skip keyword=%r: %s @ %s",
                hit,
                job.get("jobName"),
                job.get("brandName"),
            )
            continue
        if not meets_min_salary_k(str(job.get("salaryDesc") or ""), min_k=min_salary_k):
            skipped_salary += 1
            LOG.info(
                "skip salary<%.0fK: %s @ %s | %s",
                min_salary_k,
                job.get("jobName"),
                job.get("brandName"),
                job.get("salaryDesc"),
            )
            continue
        if not include_greeted and store.has_greeted(sid):
            LOG.info(
                "skip already greeted: %s @ %s",
                job.get("jobName"),
                job.get("brandName"),
            )
            continue
        targets.append(job)
        if len(targets) >= count:
            break

    LOG.info(
        "candidates=%d salary_skipped=%d keyword_skipped=%d targets=%d",
        len(jobs),
        skipped_salary,
        skipped_kw,
        len(targets),
    )
    if not targets:
        return 0

    print(f"\n将处理 {len(targets)} 个职位（{'真发' if force else 'dry-run'}）query={query!r}:\n")
    handled = 0
    for i, job in enumerate(targets, 1):
        draft = draft_greeting(job)
        print(
            f"[{i}] {job.get('jobName')} @ {job.get('brandName')} "
            f"| {job.get('salaryDesc')} | track={job.get('jobTrack')}"
        )
        print(
            f"     拟开场: {draft[:80]}…\n"
            if len(draft) > 80
            else f"     拟开场: {draft}\n"
        )

        if not force:
            audit.record(
                status="greet_dry_run",
                friend={
                    "name": job.get("bossName") or "?",
                    "brandName": job.get("brandName"),
                    "jobName": job.get("jobName"),
                },
                session_id=str(job.get("securityId")),
                question=f"[search] {query} / {city}",
                answer=draft,
            )
            handled += 1
            continue

        if not enable_greet:
            LOG.error("BOSS_ENABLE_GREET is false; refuse --force")
            return handled

        try:
            transport.greet(str(job["securityId"]), lid=str(job.get("lid") or ""))
            store.mark_greeted(
                str(job["securityId"]),
                job_name=str(job.get("jobName") or ""),
                brand=str(job.get("brandName") or ""),
                track=str(job.get("jobTrack") or ""),
            )
            LOG.info("[GREETED] %s @ %s", job.get("jobName"), job.get("brandName"))
            audit.record(
                status="greeted",
                friend={
                    "name": job.get("bossName") or "?",
                    "brandName": job.get("brandName"),
                    "jobName": job.get("jobName"),
                },
                session_id=str(job.get("securityId")),
                question=f"[search] {query} / {city}",
                answer=draft,
            )
            handled += 1
        except BossTransportError as exc:
            LOG.error("[GREET-FAIL] %s | %s", job.get("jobName"), exc)
            audit.record(
                status="greet_fail",
                friend={
                    "name": job.get("bossName") or "?",
                    "brandName": job.get("brandName"),
                    "jobName": job.get("jobName"),
                },
                session_id=str(job.get("securityId")),
                question=f"[search] {query}",
                answer=draft,
                error=str(exc),
            )
        if i < len(targets):
            time.sleep(greet_delay)
    return handled


def _run_pass(
    gcfg: GreetConfig,
    *,
    force: bool,
    include_greeted: bool,
    query_override: str | None,
    city_override: str | None,
    count_override: int | None,
) -> int:
    if not gcfg.enabled:
        LOG.warning("greet_config.enabled=false; skip")
        return 0
    if not is_within_active_hours(gcfg):
        LOG.info(
            "outside active hours %s-%s (local); skip search/greet",
            gcfg.active_start.strftime("%H:%M"),
            gcfg.active_end.strftime("%H:%M"),
        )
        return 0

    cfg = load_config()
    transport = BossTransport(cfg.boss_cli_bin, cfg.boss_cli_timeout_sec)
    store = GreetStore(_BRIDGE / "data" / "greeted.json")
    audit = AuditLog(cfg.audit_dir, phase="greet")

    queries = [query_override] if query_override else list(gcfg.queries)
    city = city_override or gcfg.city
    count = count_override if count_override is not None else gcfg.count_per_query
    total = 0
    for q in queries:
        total += _run_one_query(
            query=q,
            city=city,
            count=count,
            max_pages=gcfg.max_pages,
            min_salary_k=gcfg.min_salary_k,
            skip_keywords=gcfg.skip_keywords,
            force=force,
            include_greeted=include_greeted,
            enable_greet=cfg.enable_greet,
            greet_delay=gcfg.greet_delay_sec,
            transport=transport,
            store=store,
            audit=audit,
        )
    LOG.info("audit: %s", audit.md_path)
    return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Search jobs + greet (config-driven)")
    parser.add_argument("query", nargs="?", default=None, help="Override single query")
    parser.add_argument("--city", default=None, help="Override city")
    parser.add_argument("-n", "--count", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--include-greeted", action="store_true")
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Keep running; only search/greet inside active_hours",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to greet_config.json",
    )
    parser.add_argument(
        "--ignore-hours",
        action="store_true",
        help="Ignore active_hours (for manual dry-run outside 9-18)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    path = Path(args.config) if args.config else None
    gcfg = load_greet_config(path)
    LOG.info(
        "greet config: city=%s min_salary_k=%.0f hours=%s-%s queries=%s",
        gcfg.city,
        gcfg.min_salary_k,
        gcfg.active_start.strftime("%H:%M"),
        gcfg.active_end.strftime("%H:%M"),
        gcfg.queries,
    )

    if args.ignore_hours:
        # widen window for one-shot manual runs
        from datetime import time as dtime

        gcfg.active_start = dtime(0, 0)
        gcfg.active_end = dtime(23, 59, 59)

    if not args.loop:
        _run_pass(
            gcfg,
            force=args.force,
            include_greeted=args.include_greeted,
            query_override=args.query,
            city_override=args.city,
            count_override=args.count,
        )
        return 0

    LOG.info(
        "=== greet loop (interval=%ss, force=%s) ===",
        gcfg.loop_interval_sec,
        args.force,
    )
    while True:
        try:
            _run_pass(
                gcfg,
                force=args.force,
                include_greeted=args.include_greeted,
                query_override=args.query,
                city_override=args.city,
                count_override=args.count,
            )
        except Exception as exc:  # noqa: BLE001
            LOG.error("loop iteration failed: %s", exc)
        time.sleep(max(60, gcfg.loop_interval_sec))


if __name__ == "__main__":
    raise SystemExit(main())
