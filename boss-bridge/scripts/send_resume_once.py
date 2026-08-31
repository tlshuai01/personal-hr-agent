"""One-shot: send attachment resume to one Boss session (Geek side).

Example:
  python scripts/send_resume_once.py --session-id 2b46ad1aa7f815a21XJ73Nm4Els~
  python scripts/send_resume_once.py --session-id ... --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_BRIDGE = Path(__file__).resolve().parents[1]
if str(_BRIDGE) not in sys.path:
    sys.path.insert(0, str(_BRIDGE))

from boss_transport import BossTransport, BossTransportError  # noqa: E402
from config import load_config  # noqa: E402
from resume_select import resolve_for_friend  # noqa: E402
from session_store import SessionStore  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send Boss attachment resume once")
    parser.add_argument("--session-id", required=True, help="encryptUid / sessionId")
    parser.add_argument("--track", default="", help="force track: backend-agent|data-agent")
    parser.add_argument(
        "--user-text",
        default="",
        help="HR message (for English-resume detection / track hints)",
    )
    parser.add_argument("--resume-id", default="", help="force numeric resumeId")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve attachment only; do not POST",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Send even if history already indicates resume sent",
    )
    args = parser.parse_args(argv)

    cfg = load_config()
    transport = BossTransport(cfg.boss_cli_bin, cfg.boss_cli_timeout_sec)
    store = SessionStore(cfg.session_store_path)

    friends = transport.list_friends()
    target = next(
        (f for f in friends if str(f.get("encryptUid") or "") == args.session_id),
        None,
    )
    if not target:
        print(f"session not found: {args.session_id}", file=sys.stderr)
        return 1

    target = transport.enrich_friend_job(target)
    print(
        f"friend: {target.get('name')} @ {target.get('brandName')} | "
        f"job={target.get('jobName')} | uid={target.get('uid')}"
    )
    picked = resolve_for_friend(
        target,
        user_text=args.user_text or None,
        track=args.track or None,
    )
    print(
        f"resolved: track={picked.track} lang={picked.lang} "
        f"resumeId={picked.resume_id} name={picked.name}"
    )

    if transport.resume_already_sent(target) and not args.force:
        print("history already indicates resume sent; pass --force to override")
        return 2

    if args.dry_run:
        pending = transport.find_pending_resume_request(target)
        print("dry-run ok; pending=", json.dumps(pending, ensure_ascii=False))
        return 0

    try:
        result = transport.send_resume(
            target,
            track=args.track or picked.track,
            user_text=args.user_text or None,
            resume_id=args.resume_id or picked.resume_id,
        )
    except BossTransportError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 3

    source = str(result.get("mode") or "proactive")
    store.mark_resume_sent(
        args.session_id,
        track=str(result.get("track") or picked.track),
        source=source,
    )
    print(
        "OK:",
        json.dumps({k: v for k, v in result.items() if k != "raw"}, ensure_ascii=False),
    )
    print("local resume marked:", store.get_resume_sent(args.session_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
