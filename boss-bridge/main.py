"""Boss Bridge — phased integration with Boss 直聘 via boss-cli."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from typing import Any

from agent_client import AgentClient
from boss_transport import BossTransport, BossTransportError
from config import BridgeConfig, load_config
from policies import should_auto_reply
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
    info = friend.get("lastMessageInfo")
    if not isinstance(info, dict):
        return False
    if info.get("isSelf") is True:
        return True
    from_uid = info.get("fromUid") or info.get("fromId") or info.get("fromid")
    my_uid = friend.get("myUid") or friend.get("geekUid")
    if from_uid and my_uid and str(from_uid) == str(my_uid):
        return True
    # Boss chat list: fromType 1 = geek, 2 = boss (observed in community tools)
    from_type = info.get("fromType") or info.get("senderType")
    if str(from_type) == "1":
        return True
    return False


def _extract_incoming_message(friend: dict) -> str:
    info = friend.get("lastMessageInfo")
    if isinstance(info, dict):
        for key in ("body", "text", "content", "msg"):
            val = info.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return (friend.get("lastMsg") or "").strip()


def _needs_reply(friend: dict) -> bool:
    """Heuristic: unread from recruiter, or last turn not from geek."""
    unread = friend.get("unreadCount") or friend.get("unreadMsgCount") or 0
    try:
        if int(unread) > 0:
            incoming = _extract_incoming_message(friend)
            return not _is_system_message(incoming)
    except (TypeError, ValueError):
        pass

    if friend.get("unreplied") is True:
        return True
    if friend.get("lastSender") in ("boss", "recruiter", "them", 2, "2"):
        incoming = _extract_incoming_message(friend)
        return bool(incoming) and not _is_system_message(incoming)

    incoming = _extract_incoming_message(friend)
    if not incoming or _is_system_message(incoming):
        return False
    return not _last_message_from_self(friend)


def _build_messages(friend: dict, store: SessionStore, session_id: str) -> list[dict]:
    history = store.get_history(session_id)
    last_msg = _extract_incoming_message(friend)
    if not last_msg:
        return history
    if history and history[-1].get("role") == "user" and history[-1].get("content") == last_msg:
        return history
    history = [*history, {"role": "user", "content": last_msg}]
    return history[-20:]


def _handle_friend(
    *,
    friend: dict,
    phase: str,
    dry_run: bool,
    agent: AgentClient,
    store: SessionStore,
    transport: BossTransport,
) -> bool:
    """Process one friend. Returns True if handled (including skips marked processed)."""
    session_id = _friend_session_id(friend)
    last_msg = _extract_incoming_message(friend)
    dedupe_key = f"{session_id}:{last_msg}"
    if store.is_processed(dedupe_key):
        return False

    messages = _build_messages(friend, store, session_id)
    last_user = messages[-1]["content"] if messages else last_msg
    policy = should_auto_reply(last_user, phase=phase)
    if not policy.allowed:
        LOG.info(
            "[BLOCKED] %s | %s | reason=%s",
            session_id,
            friend.get("name"),
            policy.reason,
        )
        store.mark_processed(dedupe_key)
        return True

    try:
        result = agent.request_reply(
            session_id=session_id,
            messages=messages,
            meta={
                "bossName": friend.get("name"),
                "company": friend.get("brandName"),
                "jobTitle": friend.get("jobName") or friend.get("title"),
            },
        )
    except Exception as exc:
        LOG.error("agent reply failed for %s: %s", session_id, exc)
        return False

    if result.get("blocked"):
        LOG.info(
            "[AGENT-BLOCKED] %s | %s | %s",
            session_id,
            friend.get("name"),
            result.get("blockReason"),
        )
        store.mark_processed(dedupe_key)
        return True

    reply = (result.get("reply") or "").strip()
    if dry_run:
        LOG.info(
            "[DRY-RUN] %s | %s @ %s\n  Q: %s\n  A: %s",
            session_id,
            friend.get("name"),
            friend.get("brandName"),
            last_user[:120],
            reply[:300],
        )
        store.mark_processed(dedupe_key)
        if reply:
            store.append_assistant(session_id, reply)
        return True

    if not reply:
        store.mark_processed(dedupe_key)
        return True

    try:
        transport.send_message(friend, reply)
        LOG.info("[SENT] %s | %s | %s chars", session_id, friend.get("name"), len(reply))
        store.append_assistant(session_id, reply)
    except BossTransportError as exc:
        LOG.error("[SEND-FAIL] %s | %s", session_id, exc)
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
) -> int:
    """Single poll iteration. Returns count of friends processed."""
    friends = transport.list_friends()
    candidates = [f for f in friends if _needs_reply(f)]
    LOG.info(
        "poll: %d sessions, %d need reply%s",
        len(friends),
        len(candidates),
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
                history = _build_messages(friend, store, session_id)

            if not history:
                history = _build_messages(friend, store, session_id)

            last_user_msg = next(
                (m["content"] for m in reversed(history) if m["role"] == "user"),
                last_msg,
            )
            policy = should_auto_reply(last_user_msg, phase="c2")
            if not policy.allowed:
                LOG.info("[POLICY-BLOCKED] %s | %s", session_id, policy.reason)
                store.mark_processed(dedupe_key)
                continue

            try:
                result = agent.request_reply(
                    session_id=session_id,
                    messages=history,
                    meta={
                        "bossName": friend.get("name"),
                        "company": friend.get("brandName"),
                        "jobTitle": friend.get("jobName") or friend.get("title"),
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
                LOG.info("[DRY-RUN/C3] %s\n  A: %s", session_id, reply[:300])
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
        try:
            n = _poll_once(
                cfg,
                transport,
                agent,
                store,
                phase=poll_phase,
                dry_run=dry_run,
                limit=args.limit,
            )
        except BossTransportError as exc:
            LOG.error("poll failed: %s", exc)
            return 1
        LOG.info("done: processed %d conversations", n)
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
