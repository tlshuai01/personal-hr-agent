"""Boss 直聘 transport: direct HTTP (page=1+) + boss-cli fallback."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any
import httpx

LOG = logging.getLogger("boss-bridge.transport")

BASE_URL = "https://www.zhipin.com"
FRIEND_LIST_URL = "/wapi/zprelation/friend/getGeekFriendList.json"
CHAT_REFERER = "https://www.zhipin.com/web/geek/chat"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Origin": BASE_URL,
    "Referer": CHAT_REFERER,
}


class BossTransportError(RuntimeError):
    pass


class BossTransport:
    def __init__(self, cli_bin: str = "boss", timeout_sec: int = 60) -> None:
        self.cli_bin = cli_bin
        self.timeout_sec = timeout_sec
        if not shutil.which(cli_bin):
            LOG.warning(
                "boss-cli not found on PATH (%s). Install: pip install kabi-boss-cli",
                cli_bin,
            )

    def _run(self, *args: str) -> dict[str, Any]:
        cmd = [self.cli_bin, *args]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired as exc:
            raise BossTransportError(f"boss-cli timeout: {' '.join(cmd)}") from exc
        except FileNotFoundError as exc:
            raise BossTransportError(
                f"boss-cli not found ({self.cli_bin}). pip install kabi-boss-cli && boss login"
            ) from exc

        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()

        if proc.returncode != 0:
            raise BossTransportError(
                f"boss-cli failed ({proc.returncode}): {' '.join(cmd)}\nstderr: {stderr}\nstdout: {stdout}"
            )

        if not stdout:
            raise BossTransportError(f"boss-cli empty output: {' '.join(cmd)}")

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise BossTransportError(f"boss-cli non-json output: {stdout[:500]}") from exc

        if isinstance(payload, dict) and payload.get("ok") is False:
            raise BossTransportError(
                payload.get("error") or payload.get("message") or "boss-cli error"
            )

        return payload if isinstance(payload, dict) else {"data": payload}

    @staticmethod
    def _unwrap_list(payload: dict[str, Any]) -> list[dict]:
        data = payload.get("data", payload)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("result", "friendList", "friends", "list", "items"):
                val = data.get(key)
                if isinstance(val, list):
                    return val
        return []

    @staticmethod
    def _normalize_friend(raw: dict[str, Any]) -> dict[str, Any]:
        """Map Boss API fields onto the shape main.py expects."""
        out = dict(raw)
        if not out.get("jobName"):
            out["jobName"] = out.get("title") or out.get("sourceTitle") or ""
        if not out.get("brandName"):
            out["brandName"] = out.get("company") or ""
        # lastMessageInfo may carry richer text
        info = out.get("lastMessageInfo")
        if isinstance(info, dict) and not (out.get("lastMsg") or "").strip():
            out["lastMsg"] = (
                info.get("body") or info.get("text") or info.get("content") or ""
            )
        # unread helper for heuristics
        if "unreadCount" not in out and "unreadMsgCount" in out:
            out["unreadCount"] = out.get("unreadMsgCount")
        return out

    def status(self) -> dict[str, Any]:
        return self._run("status", "--json")

    def list_friends(self, *, max_pages: int = 3) -> list[dict]:
        """Fetch geek chat list.

        Note: Boss API returns empty zpData unless ``page`` is provided.
        boss-cli's ``boss chat`` omits page → empty list; we call HTTP directly.
        """
        cookies = self._load_cookie_dict()
        if cookies:
            try:
                friends = self._list_friends_http(cookies, max_pages=max_pages)
                if friends:
                    return friends
                LOG.warning("HTTP friend list empty; falling back to boss chat")
            except Exception as exc:  # noqa: BLE001
                LOG.warning("HTTP friend list failed (%s); falling back to boss chat", exc)

        payload = self._run("chat", "--json")
        friends = self._unwrap_list(payload)
        return [self._normalize_friend(f) for f in friends if isinstance(f, dict)]

    def _list_friends_http(self, cookies: dict[str, str], *, max_pages: int) -> list[dict]:
        all_friends: list[dict] = []
        seen: set[str] = set()
        with httpx.Client(
            base_url=BASE_URL,
            headers=DEFAULT_HEADERS,
            cookies=cookies,
            timeout=self.timeout_sec,
            follow_redirects=True,
        ) as client:
            for page in range(1, max_pages + 1):
                resp = client.get(FRIEND_LIST_URL, params={"page": page})
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") != 0:
                    raise BossTransportError(
                        f"friend list code={data.get('code')}: {data.get('message')}"
                    )
                zp = data.get("zpData") or {}
                batch = zp.get("result") if isinstance(zp, dict) else None
                if not isinstance(batch, list) or not batch:
                    break
                for item in batch:
                    if not isinstance(item, dict):
                        continue
                    key = str(
                        item.get("encryptUid")
                        or item.get("uid")
                        or item.get("securityId")
                        or id(item)
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    all_friends.append(self._normalize_friend(item))
                if len(batch) < 50:
                    # last page is usually shorter; Boss often returns 100 then less
                    break
        return all_friends

    def fetch_history(self, friend: dict, *, limit: int = 20) -> list[dict]:
        """Fetch geek↔boss chat history via HTTP; fallback to lastMsg."""
        boss_id = (
            friend.get("encryptUid")
            or friend.get("encryptBossId")
            or friend.get("encryptFriendId")
        )
        cookies = self._load_cookie_dict()
        if boss_id and cookies:
            try:
                raw = self._fetch_history_http(str(boss_id), cookies=cookies, limit=limit)
                if raw:
                    return self._normalize_history(raw, limit, boss_uid=friend.get("uid"))
            except Exception as exc:  # noqa: BLE001
                LOG.warning("HTTP history failed: %s", exc)

        friend_id = friend.get("friendId") or friend.get("encryptFriendId") or friend.get(
            "encryptUid"
        )
        if friend_id:
            for subcmd in (
                ("chat", "history", str(friend_id), "--json"),
                ("chat", "messages", str(friend_id), "--json"),
            ):
                try:
                    payload = self._run(*subcmd)
                    raw = self._unwrap_list(payload)
                    if raw:
                        return self._normalize_history(
                            raw, limit, boss_uid=friend.get("uid")
                        )
                except BossTransportError:
                    continue

        last = (friend.get("lastMsg") or "").strip()
        if last:
            return [{"role": "user", "content": last}]
        return []

    def _fetch_history_http(
        self,
        boss_id: str,
        *,
        cookies: dict[str, str],
        limit: int,
    ) -> list[dict]:
        with httpx.Client(
            base_url=BASE_URL,
            headers=DEFAULT_HEADERS,
            cookies=cookies,
            timeout=self.timeout_sec,
            follow_redirects=True,
        ) as client:
            resp = client.get(
                "/wapi/zpchat/geek/historyMsg",
                params={
                    "bossId": boss_id,
                    "maxMsgId": 0,
                    "c": max(limit, 20),
                    "page": 1,
                    "src": 0,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise BossTransportError(
                    f"history code={data.get('code')}: {data.get('message')}"
                )
            zp = data.get("zpData") or {}
            msgs = zp.get("messages")
            return msgs if isinstance(msgs, list) else []

    def resume_already_sent(self, friend: dict, *, limit: int = 40) -> bool:
        """Detect attachment resume already exchanged in this chat."""
        boss_id = friend.get("encryptUid") or friend.get("encryptBossId")
        cookies = self._load_cookie_dict()
        if not boss_id or not cookies:
            return False
        try:
            raw = self._fetch_history_http(str(boss_id), cookies=cookies, limit=limit)
        except Exception as exc:  # noqa: BLE001
            LOG.debug("resume_already_sent history failed: %s", exc)
            return False
        return history_indicates_resume_sent(raw)

    def find_pending_resume_request(self, friend: dict, *, limit: int = 40) -> dict | None:
        """Return pending HR resume-request card, or None."""
        boss_id = friend.get("encryptUid") or friend.get("encryptBossId")
        cookies = self._load_cookie_dict()
        if not boss_id or not cookies:
            return None
        try:
            raw = self._fetch_history_http(str(boss_id), cookies=cookies, limit=limit)
        except Exception as exc:  # noqa: BLE001
            LOG.debug("find_pending_resume_request failed: %s", exc)
            return None
        return find_pending_resume_request(raw)

    def send_resume(
        self,
        friend: dict,
        *,
        track: str | None = None,
        encrypt_resume_id: str | None = None,
    ) -> dict[str, Any]:
        """Send / agree to send attachment resume.

        Live HTTP path is gated and currently incomplete (Boss anti-bot / reverse TBD).
        Prefer agreeing to a pending request card (deep-link aid=38).
        """
        pending = self.find_pending_resume_request(friend)
        mode = "agree_request" if pending else "proactive"
        payload = {
            "mode": mode,
            "track": track,
            "encryptResumeId": encrypt_resume_id,
            "pending": pending,
            "bossUid": friend.get("uid"),
            "encryptUid": friend.get("encryptUid"),
        }
        # Do not hit write endpoints unless explicitly enabled at call site;
        # this method still raises until CDP/API is verified post cool-down.
        raise BossTransportError(
            "send_resume HTTP/CDP not ready: Boss returned code=36 during probe. "
            f"Prepared {mode} payload for {friend.get('name')} "
            f"(pending_mid={pending.get('mid') if pending else None}). "
            "Cool down account, then re-enable BOSS_ENABLE_SEND_RESUME after reverse is confirmed."
        )

    @staticmethod
    def _normalize_history(
        raw: list[dict],
        limit: int,
        *,
        boss_uid: Any = None,
    ) -> list[dict]:
        out: list[dict] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            body = item.get("body") if isinstance(item.get("body"), dict) else {}
            text = _message_text(item)
            if not text:
                continue
            from_obj = item.get("from") if isinstance(item.get("from"), dict) else {}
            from_uid = from_obj.get("uid") or item.get("fromUid") or item.get("fromId")
            if item.get("isSelf") is True:
                role = "assistant"
            elif item.get("isSelf") is False:
                role = "user"
            elif boss_uid is not None and from_uid is not None:
                role = "user" if str(from_uid) == str(boss_uid) else "assistant"
            else:
                sender = item.get("sender") or from_uid
                role = (
                    "assistant"
                    if str(sender).lower() in ("me", "self", "geek", "0")
                    else "user"
                )
            out.append({"role": role, "content": text})
        return out[-limit:]

    def send_message(self, friend: dict, text: str) -> None:
        """Send reply — tries boss-cli subcommand, then direct HTTP with stored cookie."""
        friend_id = (
            friend.get("friendId")
            or friend.get("encryptFriendId")
            or friend.get("uid")
            or friend.get("encryptUid")
        )
        if not friend_id:
            raise BossTransportError("friend has no id for send")

        last_err: Exception | None = None
        for subcmd in (
            ("chat", "send", str(friend_id), text, "--json"),
            ("send", str(friend_id), text, "--json"),
        ):
            try:
                self._run(*subcmd)
                return
            except BossTransportError as exc:
                last_err = exc
                LOG.debug("cli send failed (%s): %s", subcmd[0], exc)

        try:
            self._send_via_http(str(friend_id), text)
        except Exception as exc:
            raise BossTransportError(
                f"send failed for friend {friend_id}: {exc}"
            ) from (last_err or exc)

    def _send_via_http(self, friend_id: str, text: str) -> None:
        cookies = self._load_cookie_dict()
        if not cookies:
            raise BossTransportError("no boss cookie; run `boss login`")

        urls = [
            f"{BASE_URL}/wapi/zpchat/geek/send",
            f"{BASE_URL}/wapi/zpchat/geek/message/send",
        ]
        bodies = [
            {"friendId": friend_id, "msg": text},
            {"toId": friend_id, "content": text},
        ]

        with httpx.Client(
            headers=DEFAULT_HEADERS,
            cookies=cookies,
            timeout=30,
            follow_redirects=True,
        ) as client:
            for url in urls:
                for body in bodies:
                    resp = client.post(url, json=body)
                    if resp.status_code != 200:
                        continue
                    try:
                        data = resp.json()
                    except json.JSONDecodeError:
                        data = {}
                    if data.get("code") == 0:
                        return
            raise BossTransportError("HTTP send endpoints rejected request")

    def _load_cookie_dict(self) -> dict[str, str]:
        home = Path.home()
        candidates = [
            home / ".config" / "boss-cli" / "credential.json",
            home / ".config" / "boss-cli" / "credentials.json",
            home / ".boss-cli" / "credentials.json",
            home / ".kabi-boss-cli" / "credentials.json",
        ]
        for path in candidates:
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            cookies = data.get("cookies")
            if isinstance(cookies, dict) and cookies:
                return {str(k): str(v) for k, v in cookies.items() if v is not None}
            for key in ("cookie", "Cookie"):
                val = data.get(key)
                if isinstance(val, str) and val.strip():
                    return self._parse_cookie_header(val)
        return {}

    @staticmethod
    def _parse_cookie_header(header: str) -> dict[str, str]:
        out: dict[str, str] = {}
        for part in header.split(";"):
            part = part.strip()
            if not part or "=" not in part:
                continue
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
        return out

    def _load_cookie(self) -> str | None:
        cookies = self._load_cookie_dict()
        if not cookies:
            return None
        return "; ".join(f"{k}={v}" for k, v in cookies.items())


RESUME_SENT_MARKERS = (
    "对方已查看了您的附件简历",
    "您的附件简历已发送",
    "附件简历已发送给对方",
    "简历收到",
    "已收到您的附件简历",
)

RESUME_REQUEST_MARKERS = (
    "我想要一份您的附件简历",
    "请求您的附件简历",
    "请发送附件简历",
)


def _message_text(item: dict) -> str:
    body = item.get("body") if isinstance(item.get("body"), dict) else {}
    for key in ("text", "showText", "headTitle", "content", "msg"):
        val = body.get(key) if body else None
        if isinstance(val, str) and val.strip():
            return _strip_html(val.strip())
    dialog = body.get("dialog") if body else None
    if isinstance(dialog, dict):
        for key in ("text", "title", "content"):
            val = dialog.get(key)
            if isinstance(val, str) and val.strip():
                return _strip_html(val.strip())
    for key in ("body", "text", "content", "msg", "showText"):
        val = item.get(key)
        if isinstance(val, str) and val.strip():
            return _strip_html(val.strip())
    return ""


def _strip_html(text: str) -> str:
    import re

    return re.sub(r"<[^>]+>", "", text.replace("&nbsp;", " ")).strip()


def history_indicates_resume_sent(raw: list[dict]) -> bool:
    """True if geek already sent / agreed to send attachment resume.

    HR request-only cards (我想要一份您的附件简历) do NOT count as sent.
    """
    for item in raw:
        if not isinstance(item, dict):
            continue
        blob = json.dumps(item, ensure_ascii=False)
        if any(m in blob for m in RESUME_SENT_MARKERS):
            return True
        if "encryptResumeId" in blob or "resumePreview" in blob:
            return True
        if '"aid": 38' in blob or '"aid":38' in blob:
            # aid=38 = 同意发送附件简历（实测）
            return True
        body = item.get("body") if isinstance(item.get("body"), dict) else {}
        action = body.get("action") if isinstance(body.get("action"), dict) else {}
        if str(action.get("aid")) == "38":
            return True
        hyper = body.get("hyperLink") if isinstance(body.get("hyperLink"), dict) else {}
        extra = str(hyper.get("extraJson") or "")
        if "encryptResumeId" in extra or "attach-resume" in extra:
            return True
    return False


def find_pending_resume_request(raw: list[dict]) -> dict[str, Any] | None:
    """Find HR attachment-resume request card that is not yet operated.

    Deep-link shape (实测): bosszp://...type=sendaction&uid=<bossUid>&aid=38
    """
    for item in reversed(raw):
        if not isinstance(item, dict):
            continue
        body = item.get("body") if isinstance(item.get("body"), dict) else {}
        dialog = body.get("dialog") if isinstance(body.get("dialog"), dict) else None
        if not dialog:
            continue
        text = str(dialog.get("text") or dialog.get("title") or "")
        if not any(m in text for m in RESUME_REQUEST_MARKERS):
            buttons = dialog.get("buttons") if isinstance(dialog.get("buttons"), list) else []
            blob = json.dumps(buttons, ensure_ascii=False)
            if "aid=38" not in blob and "aid%3D38" not in blob:
                continue
        if dialog.get("operated") is True:
            continue
        buttons = dialog.get("buttons") if isinstance(dialog.get("buttons"), list) else []
        agree_url = ""
        for btn in buttons:
            if not isinstance(btn, dict):
                continue
            url = str(btn.get("url") or "")
            if "aid=38" in url or "aid%3D38" in url:
                agree_url = url
                break
        if not agree_url:
            continue
        return {
            "mid": item.get("mid"),
            "bossUid": _boss_uid_from_sendaction(agree_url)
            or ((item.get("from") or {}).get("uid") if isinstance(item.get("from"), dict) else None),
            "agreeUrl": agree_url,
            "text": text,
        }
    return None


def _boss_uid_from_sendaction(url: str) -> Any:
    import re

    m = re.search(r"[?&]uid=(\d+)", url)
    return int(m.group(1)) if m else None


def extract_encrypt_resume_ids(raw: list[dict]) -> list[str]:
    """Collect encryptResumeId seen in chat (last sent attachment)."""
    import re

    found: list[str] = []
    for item in raw:
        blob = json.dumps(item, ensure_ascii=False)
        for m in re.finditer(r"encryptResumeId[=:\\\"]+(\w[\w~-]*)", blob):
            rid = m.group(1).rstrip("\\")
            if rid and rid not in found:
                found.append(rid)
    return found
