"""Boss 直聘 transport: HTTP (page=1+) + MQTT text + boss-cli fallback."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

from boss_http import (
    CHAT_REFERER,
    BossHttpClient,
    BossHttpError,
)
from mqtt_chat import BossMQTTChat

LOG = logging.getLogger("boss-bridge.transport")

FRIEND_LIST_URL = "/wapi/zprelation/friend/getGeekFriendList.json"
HISTORY_MSG_URL = "/wapi/zpchat/geek/historyMsg"
LAST_MSG_URL = "/wapi/zpchat/geek/userLastMsg"
USER_INFO_URL = "/wapi/zpuser/wap/getUserInfo.json"
WT_URL = "/wapi/zppassport/get/wt"


class BossTransportError(RuntimeError):
    pass


class BossTransport:
    def __init__(self, cli_bin: str = "boss", timeout_sec: int = 60) -> None:
        self.cli_bin = cli_bin
        self.timeout_sec = timeout_sec
        self._my_uid: int | None = None
        self._my_encrypt_uid: str | None = None
        if not shutil.which(cli_bin):
            LOG.warning(
                "boss-cli not found on PATH (%s). Install: pip install kabi-boss-cli",
                cli_bin,
            )

    def _http(self, cookies: dict[str, str] | None = None) -> BossHttpClient:
        jar = cookies if cookies is not None else self._load_cookie_dict()
        if not jar:
            raise BossTransportError("no boss cookie; run `boss login`")
        return BossHttpClient(jar, timeout=float(self.timeout_sec))

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
        with self._http(cookies) as client:
            for page in range(1, max_pages + 1):
                try:
                    zp = client.get(
                        FRIEND_LIST_URL,
                        action="friend list",
                        params={"page": page},
                        referer=CHAT_REFERER,
                    )
                except BossHttpError as exc:
                    raise BossTransportError(str(exc)) from exc
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
                    break
        return all_friends

    def enrich_last_messages(self, friends: list[dict], *, batch_size: int = 20) -> list[dict]:
        """Merge /wapi/zpchat/geek/userLastMsg into friend.lastMessageInfo (in place)."""
        cookies = self._load_cookie_dict()
        if not cookies or not friends:
            return friends
        uids = []
        by_uid: dict[str, dict] = {}
        for f in friends:
            uid = f.get("uid") or f.get("friendId")
            if uid is None:
                continue
            uids.append(int(uid))
            by_uid[str(uid)] = f
        if not uids:
            return friends

        my_uid = self._ensure_my_identity(cookies).get("userId")
        with self._http(cookies) as client:
            for i in range(0, len(uids), batch_size):
                chunk = uids[i : i + batch_size]
                try:
                    zp = client.get(
                        LAST_MSG_URL,
                        action="userLastMsg",
                        params={"friendIds": ",".join(str(u) for u in chunk)},
                        referer=CHAT_REFERER,
                    )
                except BossHttpError as exc:
                    LOG.warning("userLastMsg failed: %s", exc)
                    break
                # zpData may be list directly via _raw, or under a key
                rows: list = []
                if isinstance(zp.get("_raw"), list):
                    rows = zp["_raw"]
                elif isinstance(zp, list):
                    rows = zp
                else:
                    for key in ("result", "list", "messages", "friendList"):
                        val = zp.get(key)
                        if isinstance(val, list):
                            rows = val
                            break
                    if not rows and zp:
                        # sometimes zpData is the list returned as non-dict — handled above
                        pass
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    info = row.get("lastMsgInfo") or row.get("lastMessageInfo") or {}
                    if not isinstance(info, dict):
                        continue
                    from_id = info.get("fromId") or info.get("fromUid")
                    to_id = info.get("toId") or info.get("toUid")
                    peer = None
                    if my_uid is not None and from_id is not None and to_id is not None:
                        peer = to_id if str(from_id) == str(my_uid) else from_id
                    if peer is None:
                        peer = row.get("friendId") or row.get("uid")
                    friend = by_uid.get(str(peer))
                    if not friend:
                        continue
                    friend["lastMessageInfo"] = info
                    text = (
                        info.get("showText")
                        or info.get("body")
                        or info.get("text")
                        or ""
                    )
                    if text:
                        friend["lastMsg"] = text
                    if row.get("lastTime"):
                        friend["lastTime"] = row.get("lastTime")
        return friends

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
                raw = self._fetch_history_http(
                    str(boss_id),
                    cookies=cookies,
                    limit=limit,
                    numeric_uid=int(friend["uid"])
                    if friend.get("uid") is not None
                    else None,
                )
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
        numeric_uid: int | None = None,
    ) -> list[dict]:
        """Fetch history with maxMsgId pagination (zhipin-geek style)."""
        page_size = min(max(limit, 1), 20)
        all_msgs: list[dict] = []
        max_msg_id = 0
        security_id = ""
        if numeric_uid is not None:
            try:
                security_id = self._fetch_boss_security_id(int(numeric_uid), cookies)
            except Exception:  # noqa: BLE001
                security_id = ""

        with self._http(cookies) as client:
            for _ in range(50):
                params: dict[str, Any] = {
                    "bossId": boss_id,
                    "c": page_size,
                    "page": 1,
                    "src": 0,
                }
                if max_msg_id:
                    params["maxMsgId"] = max_msg_id
                else:
                    params["maxMsgId"] = 0
                if security_id:
                    params["securityId"] = security_id
                if numeric_uid is not None:
                    params["gid"] = numeric_uid
                try:
                    zp = client.get(
                        HISTORY_MSG_URL,
                        action="historyMsg",
                        params=params,
                        referer=CHAT_REFERER,
                    )
                except BossHttpError as exc:
                    raise BossTransportError(str(exc)) from exc
                batch = zp.get("messages") if isinstance(zp.get("messages"), list) else []
                if not batch and isinstance(zp.get("msgList"), list):
                    batch = zp["msgList"]
                if not batch:
                    break
                all_msgs.extend(batch)
                if len(all_msgs) >= limit:
                    return all_msgs[:limit]
                next_id = zp.get("minMsgId") or 0
                if not next_id and batch:
                    last = batch[-1]
                    next_id = last.get("mid") or last.get("msgId") or last.get("id") or 0
                if not next_id or next_id == max_msg_id:
                    break
                max_msg_id = next_id
        return all_msgs[:limit]

    def resume_already_sent(self, friend: dict, *, limit: int = 40) -> bool:
        """Detect attachment resume already exchanged in this chat."""
        boss_id = friend.get("encryptUid") or friend.get("encryptBossId")
        cookies = self._load_cookie_dict()
        if not boss_id or not cookies:
            return False
        try:
            raw = self._fetch_history_http(
                str(boss_id),
                cookies=cookies,
                limit=limit,
                numeric_uid=int(friend["uid"]) if friend.get("uid") is not None else None,
            )
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
            raw = self._fetch_history_http(
                str(boss_id),
                cookies=cookies,
                limit=limit,
                numeric_uid=int(friend["uid"]) if friend.get("uid") is not None else None,
            )
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
        resume_id: str | None = None,
        user_text: str | None = None,
    ) -> dict[str, Any]:
        """Send / agree to send attachment resume (Geek side).

        Proactive: ``POST /wapi/zpchat/exchange/request`` with ``type=3``
        (aligned with zhipin-geek). Agree: ``acceptItemContact`` when HR
        request card is pending (aid=38).

        Picks attachment by JD track + language (English only when explicitly
        requested). Callers must gate with ``BOSS_ENABLE_SEND_RESUME``.
        """
        from resume_select import resolve_for_friend

        boss_id = friend.get("uid") or friend.get("friendId")
        if boss_id is None:
            raise BossTransportError("friend has no uid for send_resume")
        boss_id_int = int(boss_id)

        cookies = self._load_cookie_dict()
        if not cookies:
            raise BossTransportError("no boss cookie; run `boss login`")

        friend = self.enrich_friend_job(friend)

        security_id = self._fetch_boss_security_id(boss_id_int, cookies)
        if not security_id:
            security_id = str(friend.get("securityId") or "").strip()
        if not security_id:
            raise BossTransportError(
                f"no securityId for boss uid={boss_id_int} ({friend.get('name')})"
            )

        attachment = resolve_for_friend(friend, user_text=user_text, track=track)
        chosen_resume_id = (
            str(resume_id or encrypt_resume_id or attachment.resume_id).strip()
        )
        if not chosen_resume_id:
            raise BossTransportError("no resumeId resolved for send_resume")

        pending = self.find_pending_resume_request(friend)
        mode = "agree_request" if pending else "proactive"

        try:
            with self._http(cookies) as client:
                if pending and pending.get("mid") is not None:
                    zp = client.post_form(
                        "/wapi/zpchat/geek/acceptItemContact",
                        {
                            "bossId": str(boss_id_int),
                            "mid": str(pending["mid"]),
                            "securityId": security_id,
                            "resumeId": chosen_resume_id,
                        },
                        action="accept resume",
                        referer=CHAT_REFERER,
                    )
                else:
                    zp = client.post_form(
                        "/wapi/zpchat/exchange/request",
                        {
                            "type": "3",
                            "bossId": str(boss_id_int),
                            "securityId": security_id,
                            "resumeId": chosen_resume_id,
                        },
                        action="send resume",
                        referer=CHAT_REFERER,
                    )
        except BossHttpError as exc:
            raise BossTransportError(str(exc)) from exc

        status = zp.get("status") if isinstance(zp, dict) else None
        return {
            "mode": mode,
            "track": attachment.track,
            "lang": attachment.lang,
            "resumeId": chosen_resume_id,
            "resumeName": attachment.name,
            "bossUid": boss_id_int,
            "encryptUid": friend.get("encryptUid"),
            "pending": pending,
            "apiCode": 0,
            "apiStatus": status,
            "raw": zp,
        }

    def _fetch_boss_security_id(
        self, boss_id: int, cookies: dict[str, str]
    ) -> str:
        data = self._fetch_boss_data(boss_id, cookies)
        return str(data.get("securityId") or "").strip()

    def _fetch_boss_data(
        self, boss_id: int, cookies: dict[str, str]
    ) -> dict[str, Any]:
        """Return getBossData.zpData.data (+ job) flattened fields we care about."""
        try:
            with self._http(cookies) as client:
                zp = client.get(
                    "/wapi/zpchat/geek/getBossData",
                    action="getBossData",
                    params={"bossId": boss_id},
                    referer=CHAT_REFERER,
                )
        except BossHttpError as exc:
            LOG.debug("getBossData failed: %s", exc)
            return {}
        nested = zp.get("data") if isinstance(zp.get("data"), dict) else {}
        job = zp.get("job") if isinstance(zp.get("job"), dict) else {}
        out = dict(nested) if nested else {}
        if job.get("jobName"):
            out["jobName"] = job.get("jobName")
        if job.get("salaryDesc"):
            out["salaryDesc"] = job.get("salaryDesc")
        return out

    def enrich_friend_job(self, friend: dict) -> dict:
        """Prefer real JD jobName from getBossData over list title (often HR title)."""
        out = dict(friend)
        boss_id = friend.get("uid") or friend.get("friendId")
        cookies = self._load_cookie_dict()
        if boss_id is None or not cookies:
            return out
        try:
            data = self._fetch_boss_data(int(boss_id), cookies)
        except Exception as exc:  # noqa: BLE001
            LOG.debug("enrich_friend_job failed: %s", exc)
            return out
        job_name = str(data.get("jobName") or "").strip()
        if job_name:
            out["jobName"] = job_name
            out["_jobNameFromBossData"] = True
        if data.get("salaryDesc"):
            out["salaryDesc"] = data.get("salaryDesc")
        if data.get("securityId") and not out.get("securityId"):
            out["securityId"] = data.get("securityId")
        return out

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
        """Send reply — MQTT first (zhipin-geek), then CLI, then legacy HTTP."""
        cookies = self._load_cookie_dict()
        last_err: Exception | None = None

        if cookies:
            try:
                self._send_via_mqtt(friend, text, cookies)
                return
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                LOG.warning("MQTT send failed, falling back: %s", exc)

        friend_id = (
            friend.get("friendId")
            or friend.get("encryptFriendId")
            or friend.get("uid")
            or friend.get("encryptUid")
        )
        if not friend_id:
            raise BossTransportError("friend has no id for send") from last_err

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
            self._send_via_http(str(friend_id), text, cookies)
        except Exception as exc:
            raise BossTransportError(
                f"send failed for friend {friend_id}: {exc}"
            ) from (last_err or exc)

    def _ensure_my_identity(self, cookies: dict[str, str]) -> dict[str, Any]:
        if self._my_uid is not None and self._my_encrypt_uid:
            return {
                "userId": self._my_uid,
                "encryptUserId": self._my_encrypt_uid,
            }
        with self._http(cookies) as client:
            info = client.get(
                USER_INFO_URL, action="getUserInfo", referer=CHAT_REFERER
            )
        uid = info.get("userId") or info.get("uid")
        enc = str(info.get("encryptUserId") or info.get("encryptUid") or "")
        if uid is None:
            raise BossTransportError("getUserInfo missing userId")
        self._my_uid = int(uid)
        self._my_encrypt_uid = enc
        return {"userId": self._my_uid, "encryptUserId": enc}

    def _get_ws_auth(self, cookies: dict[str, str]) -> tuple[str, str]:
        with self._http(cookies) as client:
            info = client.get(
                USER_INFO_URL, action="getUserInfo", referer=CHAT_REFERER
            )
            page_token = str(info.get("token") or "")
            wt = client.get(WT_URL, action="get/wt", referer=CHAT_REFERER)
            wt2 = str(wt.get("wt2") or cookies.get("wt2") or "")
        if not page_token or not wt2:
            raise BossTransportError("MQTT auth missing page_token or wt2")
        uid = info.get("userId") or info.get("uid")
        enc = str(info.get("encryptUserId") or info.get("encryptUid") or "")
        if uid is not None:
            self._my_uid = int(uid)
            self._my_encrypt_uid = enc
        return page_token, wt2

    def _send_via_mqtt(
        self, friend: dict, text: str, cookies: dict[str, str]
    ) -> None:
        to_uid = friend.get("uid") or friend.get("friendId")
        to_enc = str(
            friend.get("encryptUid")
            or friend.get("encryptFriendId")
            or friend.get("encryptBossId")
            or ""
        )
        if to_uid is None:
            raise BossTransportError("friend uid required for MQTT send")
        page_token, wt2 = self._get_ws_auth(cookies)
        me = self._ensure_my_identity(cookies)
        with BossMQTTChat(page_token, wt2, cookies=cookies, timeout=12.0) as chat:
            chat.send(
                from_uid=int(me["userId"]),
                from_encrypt_uid=str(me.get("encryptUserId") or ""),
                to_uid=int(to_uid),
                to_encrypt_uid=to_enc,
                text=text,
            )

    def _send_via_http(
        self, friend_id: str, text: str, cookies: dict[str, str] | None = None
    ) -> None:
        jar = cookies or self._load_cookie_dict()
        if not jar:
            raise BossTransportError("no boss cookie; run `boss login`")

        urls = [
            "/wapi/zpchat/geek/send",
            "/wapi/zpchat/geek/message/send",
        ]
        bodies = [
            {"friendId": friend_id, "msg": text},
            {"toId": friend_id, "content": text},
        ]
        with self._http(jar) as client:
            for url in urls:
                for body in bodies:
                    try:
                        client.post_form(
                            url,
                            {k: str(v) for k, v in body.items()},
                            action="legacy text send",
                            referer=CHAT_REFERER,
                        )
                        return
                    except BossHttpError:
                        continue
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
