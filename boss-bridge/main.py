"""Boss Bridge — phased integration with Boss 直聘 via boss-cli."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

from agent_client import AgentClient
from boss_transport import BossTransport, BossTransportError
from config import BridgeConfig, load_config
from policies import should_auto_reply
from report_writer import DryRunReport
from session_store import SessionStore

LOG = logging.getLogger("boss-bridge")

SYSTEM_MSG_MARKERS = (
    "对方已同意",
    "您的附件简历已发送",
    "撤回了一条消息",
    "交换联系方式",
    "请求交换",
)


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def phase_c0(cfg: BridgeConfig, transport: BossTransport) -> int:
    """Verify login and list chat sessions."""
    LOG.info("=== C0: login + session list ===")
    status = transport.status()
    LOG.info("boss status: %s", json.dumps(status, ensure_ascii=False, indent=2))

    friends = transport.list_friends()
    LOG.info("found %d chat sessions", len(friends))
    unread_total = sum(
        int(f.get("unreadMsgCount") or f.get("unreadCount") or 0) for f in friends
    )
    LOG.info("unread sessions (sum of unreadMsgCount): %d", unread_total)

    for i, f in enumerate(friends[:20], 1):
        LOG.info(
            "  [%d] %s @ %s | job=%s | last=%s",
            i,
            f.get("name", "?"),
            f.get("brandName", "?"),
            f.get("jobName") or f.get("title") or "?",
            (f.get("lastMsg") or "")[:80],
        )
        unread = f.get("unreadMsgCount") or f.get("unreadCount") or 0
        if unread:
            LOG.info("       unread=%s", unread)
    if len(friends) > 20:
        LOG.info("  ... and %d more", len(friends) - 20)
    return 0


def _friend_session_id(friend: dict) -> str:
    for key in ("encryptUid", "encryptFriendId", "friendId", "uid"):
        val = friend.get(key)
        if val:
            return str(val)
    name = friend.get("name") or "unknown"
    brand = friend.get("brandName") or ""
    return f"{name}:{brand}"


def _is_system_message(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    return any(marker in t for marker in SYSTEM_MSG_MARKERS)


def _last_message_from_self(friend: dict) -> bool:
    """Geek 沟通列表：friend.uid 是 Boss；自己发的消息 fromId != boss.uid。"""
    info = friend.get("lastMessageInfo")
    if not isinstance(info, dict):
        return False
    if info.get("isSelf") is True:
        return True
    if info.get("isSelf") is False:
        return False

    boss_uid = friend.get("uid")
    from_id = info.get("fromId") or info.get("fromUid") or info.get("fromid")
    to_id = info.get("toId") or info.get("toUid")

    # 主判定：发送方不是 Boss → 视为自己（Geek）发出
    if boss_uid is not None and from_id is not None:
        return str(from_id) != str(boss_uid)

    # 次判定：收件人是 Boss → 自己发出
    if boss_uid is not None and to_id is not None and str(to_id) == str(boss_uid):
        return True

    from_type = info.get("fromType") or info.get("senderType")
    if str(from_type) == "1":
        return True
    return False


def _extract_incoming_message(friend: dict) -> str:
    info = friend.get("lastMessageInfo")
    if isinstance(info, dict):
        for key in ("showText", "body", "text", "content", "msg"):
            val = info.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return (friend.get("lastMsg") or "").strip()


def _needs_reply(friend: dict) -> bool:
    """仅当最后一条是 HR/Boss 发来的才回复；自己发的绝不回。"""
    if _last_message_from_self(friend):
        return False

    incoming = _extract_incoming_message(friend)
    if not incoming or _is_system_message(incoming):
        return False

    unread = friend.get("unreadCount") or friend.get("unreadMsgCount") or 0
    try:
        if int(unread) > 0:
            return True
    except (TypeError, ValueError):
        pass

    if friend.get("unreplied") is True:
        return True
    if friend.get("lastSender") in ("boss", "recruiter", "them", 2, "2"):
        return True

    # 最后一条已判定来自 Boss（非 self），即使未读为 0 也可回复一次（如拒信）
    return True


def _build_messages(friend: dict, store: SessionStore, session_id: str, transport: BossTransport) -> list[dict]:
    """Prefer live Boss history; fall back to local short memory + lastMsg."""
    try:
        live = transport.fetch_history(friend, limit=20)
    except Exception:  # noqa: BLE001
        live = []
    if live:
        store.sync_history(session_id, live)
        return live

    history = store.get_history(session_id)
    last_msg = _extract_incoming_message(friend)
    if not last_msg:
        return history
    if history and history[-1].get("role") == "user" and history[-1].get("content") == last_msg:
        return history
    history = [*history, {"role": "user", "content": last_msg}]
    return history[-20:]


def _resolve_resume_already_sent(
    friend: dict,
    store: SessionStore,
    session_id: str,
    transport: BossTransport,
) -> bool:
    """Local resumeSentAt first; else history heuristic and bootstrap store."""
    local = store.get_resume_sent(session_id)
    if local:
        LOG.info(
            "resume_already_sent local %s source=%s",
            session_id,
            local.get("resumeSource"),
        )
        return True

    try:
        hit = transport.resume_already_sent(friend, limit=40)
    except Exception as exc:  # noqa: BLE001
        LOG.debug("resume_already_sent failed: %s", exc)
        return False

    if hit:
        store.mark_resume_sent(session_id, source="history_bootstrap")
        LOG.info(
            "resume_already_sent bootstrap %s (history → local)",
            session_id,
        )
    return hit


def _handle_friend(
    *,
    friend: dict,
    phase: str,
    dry_run: bool,
    agent: AgentClient,
    store: SessionStore,
    transport: BossTransport,
    report: DryRunReport | None = None,
    ignore_processed: bool = False,
    enable_send_resume: bool = False,
) -> bool:
    """Process one friend. Returns True if handled (including skips marked processed)."""
    session_id = _friend_session_id(friend)
    last_msg = _extract_incoming_message(friend)
    dedupe_key = f"{session_id}:{last_msg}"
    if not ignore_processed and store.is_processed(dedupe_key):
        return False

    messages = _build_messages(friend, store, session_id, transport)
    last_user = messages[-1]["content"] if messages else last_msg
    policy = should_auto_reply(last_user, phase=phase)
    if not policy.allowed:
        LOG.info(
            "[BLOCKED] %s | %s | reason=%s",
            session_id,
            friend.get("name"),
            policy.reason,
        )
        if report:
            report.add(
                status="policy_blocked",
                friend=friend,
                session_id=session_id,
                question=last_user,
                block_reason=policy.reason or "",
            )
        store.mark_processed(dedupe_key)
        return True

    resume_sent = _resolve_resume_already_sent(friend, store, session_id, transport)

    try:
        result = agent.request_reply(
            session_id=session_id,
            messages=messages,
            meta={
                "bossName": friend.get("name"),
                "company": friend.get("brandName"),
                "jobTitle": friend.get("jobName") or friend.get("title"),
                "resumeAlreadySent": resume_sent,
            },
        )
    except Exception as exc:
        LOG.error("agent reply failed for %s: %s", session_id, exc)
        if report:
            report.add(
                status="error",
                friend=friend,
                session_id=session_id,
                question=last_user,
                error=str(exc),
            )
        # Count toward --limit so one Core outage doesn't scan all candidates
        return True

    if result.get("blocked"):
        LOG.info(
            "[AGENT-BLOCKED] %s | %s | %s",
            session_id,
            friend.get("name"),
            result.get("blockReason"),
        )
        if report:
            report.add(
                status="agent_blocked",
                friend=friend,
                session_id=session_id,
                question=last_user,
                block_reason=str(result.get("blockReason") or ""),
            )
        store.mark_processed(dedupe_key)
        return True

    reply = (result.get("reply") or "").strip()
    sources = list(result.get("sources") or [])
    actions = list(result.get("actions") or [])
    send_resume_actions = [
        a
        for a in actions
        if isinstance(a, dict) and a.get("type") == "send_resume"
    ]

    if dry_run:
        action_note = ""
        if resume_sent:
            action_note += " | resume_already_sent"
        for act in send_resume_actions:
            action_note += f" | resume={act.get('label') or act.get('track')}"
            # dry-run: never call Boss; only report intent
        LOG.info(
            "[DRY-RUN] %s | %s @ %s%s\n  Q: %s\n  A: %s",
            session_id,
            friend.get("name"),
            friend.get("brandName"),
            action_note,
            last_user[:120],
            reply[:300],
        )
        if report:
            report.add(
                status="dry_run",
                friend=friend,
                session_id=session_id,
                question=last_user,
                answer=reply,
                sources=sources,
                actions=actions if isinstance(actions, list) else [],
                resume_already_sent=resume_sent,
            )
        store.mark_processed(dedupe_key)
        if reply:
            store.append_assistant(session_id, reply)
        return True

    if not reply and not send_resume_actions:
        store.mark_processed(dedupe_key)
        return True

    if reply:
        try:
            transport.send_message(friend, reply)
            LOG.info("[SENT] %s | %s | %s chars", session_id, friend.get("name"), len(reply))
            store.append_assistant(session_id, reply)
        except BossTransportError as exc:
            LOG.error("[SEND-FAIL] %s | %s", session_id, exc)
            return False

    if send_resume_actions and not resume_sent:
        track = str(send_resume_actions[0].get("track") or "")
        if not enable_send_resume:
            LOG.info(
                "[RESUME-SKIP] %s enable_send_resume=false (would send %s)",
                session_id,
                track or send_resume_actions[0].get("label"),
            )
        else:
            pending = transport.find_pending_resume_request(friend)
            source = "agree_request" if pending else "proactive"
            try:
                transport.send_resume(friend, track=track or None)
                store.mark_resume_sent(
                    session_id, track=track or None, source=source
                )
                LOG.info("[RESUME-SENT] %s track=%s source=%s", session_id, track, source)
            except BossTransportError as exc:
                LOG.error("[RESUME-FAIL] %s | %s", session_id, exc)
                # text already sent; still mark processed
                store.mark_processed(dedupe_key)
                return False

    store.mark_processed(dedupe_key)
    return True


def _poll_once(
    cfg: BridgeConfig,
    transport: BossTransport,
    agent: AgentClient,
    store: SessionStore,
    *,
    phase: str,
    dry_run: bool,
    limit: int | None = None,
    report: DryRunReport | None = None,
    ignore_processed: bool = False,
) -> int:
    """Single poll iteration. Returns count of friends processed."""
    friends = transport.list_friends()
    candidates = [f for f in friends if _needs_reply(f)]
    skipped_self = sum(1 for f in friends if _last_message_from_self(f))
    if report:
        report.total_sessions = len(friends)
        report.candidates = len(candidates)
    LOG.info(
        "poll: %d sessions, %d need reply, %d last-from-self(skipped)%s",
        len(friends),
        len(candidates),
        skipped_self,
        f", processing up to {limit}" if limit else "",
    )

    processed = 0
    for friend in candidates:
        if limit is not None and processed >= limit:
            break
        if _handle_friend(
            friend=friend,
            phase=phase,
            dry_run=dry_run,
            agent=agent,
            store=store,
            transport=transport,
            report=report,
            ignore_processed=ignore_processed,
            enable_send_resume=cfg.enable_send_resume,
        ):
            processed += 1
            if not dry_run:
                time.sleep(cfg.send_delay_sec)
    return processed


def phase_c1_loop(cfg: BridgeConfig, transport: BossTransport, agent: AgentClient, store: SessionStore) -> None:
    """Poll unread, generate reply via agent, log only (dry-run)."""
    LOG.info("=== C1: dry-run loop (poll=%ss) ===", cfg.poll_interval_sec)
    while True:
        try:
            _poll_once(cfg, transport, agent, store, phase="c1", dry_run=True)
        except BossTransportError as exc:
            LOG.error("list friends failed: %s", exc)
        time.sleep(cfg.poll_interval_sec)


def phase_c2_loop(cfg: BridgeConfig, transport: BossTransport, agent: AgentClient, store: SessionStore) -> None:
    """Auto-send non-sensitive replies; sensitive → blocked log only."""
    LOG.info("=== C2: auto-reply loop (poll=%ss) ===", cfg.poll_interval_sec)
    while True:
        try:
            _poll_once(cfg, transport, agent, store, phase="c2", dry_run=False)
        except BossTransportError as exc:
            LOG.error("list friends failed: %s", exc)
        time.sleep(cfg.poll_interval_sec)


def phase_c3_loop(cfg: BridgeConfig, transport: BossTransport, agent: AgentClient, store: SessionStore) -> None:
    """Multi-turn: fetch chat history per session before replying."""
    LOG.info("=== C3: multi-turn loop (poll=%ss) ===", cfg.poll_interval_sec)
    while True:
        try:
            friends = transport.list_friends()
        except BossTransportError as exc:
            LOG.error("list friends failed: %s", exc)
            time.sleep(cfg.poll_interval_sec)
            continue

        for friend in friends:
            if not _needs_reply(friend):
                continue

            session_id = _friend_session_id(friend)
            last_msg = _extract_incoming_message(friend)
            dedupe_key = f"{session_id}:{last_msg}"
            if store.is_processed(dedupe_key):
                continue

            try:
                history = transport.fetch_history(friend, limit=cfg.history_limit)
            except BossTransportError:
                history = _build_messages(friend, store, session_id, transport)

            if not history:
                history = _build_messages(friend, store, session_id, transport)

            last_user_msg = next(
                (m["content"] for m in reversed(history) if m["role"] == "user"),
                last_msg,
            )
            policy = should_auto_reply(last_user_msg, phase="c2")
            if not policy.allowed:
                LOG.info("[POLICY-BLOCKED] %s | %s", session_id, policy.reason)
                store.mark_processed(dedupe_key)
                continue

            resume_sent = _resolve_resume_already_sent(
                friend, store, session_id, transport
            )

            try:
                result = agent.request_reply(
                    session_id=session_id,
                    messages=history,
                    meta={
                        "bossName": friend.get("name"),
                        "company": friend.get("brandName"),
                        "jobTitle": friend.get("jobName") or friend.get("title"),
                        "resumeAlreadySent": resume_sent,
                    },
                )
            except Exception as exc:
                LOG.error("agent reply failed for %s: %s", session_id, exc)
                continue

            store.sync_history(session_id, history)

            if result.get("blocked"):
                LOG.info("[AGENT-BLOCKED] %s | %s", session_id, result.get("blockReason"))
                store.mark_processed(dedupe_key)
                continue

            reply = (result.get("reply") or "").strip()
            dry = cfg.phase == "c1"
            if dry:
                note = " | resume_already_sent" if resume_sent else ""
                LOG.info("[DRY-RUN/C3] %s%s\n  A: %s", session_id, note, reply[:300])
            elif reply:
                try:
                    transport.send_message(friend, reply)
                    LOG.info("[SENT/C3] %s | %s chars", session_id, len(reply))
                except BossTransportError as exc:
                    LOG.error("[SEND-FAIL] %s | %s", session_id, exc)

            if reply:
                store.append_assistant(session_id, reply)
            store.mark_processed(dedupe_key)
            if not dry:
                time.sleep(cfg.send_delay_sec)

        time.sleep(cfg.poll_interval_sec)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Boss Bridge — phased Boss 直聘 integration")
    parser.add_argument(
        "--phase",
        choices=["c0", "c1", "c2", "c3"],
        default="c1",
        help="c0=login+list, c1=dry-run, c2=auto-send, c3=multi-turn (default: c1)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single poll iteration then exit (C1/C2/C3)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Max conversations to process per --once run (default: 3)",
    )
    parser.add_argument(
        "--report",
        metavar="PATH",
        help="Write dry-run review markdown to PATH (use with --once)",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Ignore prior processed dedupe keys for this run (for report re-runs)",
    )
    args = parser.parse_args(argv)

    cfg = load_config()
    cfg.phase = args.phase
    setup_logging(cfg.log_level)

    transport = BossTransport(cfg.boss_cli_bin, cfg.boss_cli_timeout_sec)
    store = SessionStore(cfg.session_store_path)
    agent = AgentClient(cfg.agent_base_url, cfg.boss_bridge_secret, cfg.agent_timeout_sec)

    if args.phase == "c0":
        return phase_c0(cfg, transport)

    dry_run = args.phase == "c1"
    poll_phase = "c1" if args.phase == "c1" else "c2"

    if args.once:
        LOG.info("=== %s: single poll (--limit %d) ===", args.phase.upper(), args.limit)
        report: DryRunReport | None = None
        if args.report:
            report = DryRunReport(
                phase=args.phase,
                limit=args.limit,
                total_sessions=0,
                candidates=0,
            )
        try:
            n = _poll_once(
                cfg,
                transport,
                agent,
                store,
                phase=poll_phase,
                dry_run=dry_run,
                limit=args.limit,
                report=report,
                ignore_processed=args.fresh,
            )
        except BossTransportError as exc:
            LOG.error("poll failed: %s", exc)
            return 1
        LOG.info("done: processed %d conversations", n)
        if report:
            out = Path(args.report)
            report.write_markdown(out)
            LOG.info("report written: %s", out.resolve())
        return 0

    if args.phase == "c1":
        phase_c1_loop(cfg, transport, agent, store)
        return 0

    if args.phase == "c2":
        phase_c2_loop(cfg, transport, agent, store)
        return 0

    if args.phase == "c3":
        phase_c3_loop(cfg, transport, agent, store)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
