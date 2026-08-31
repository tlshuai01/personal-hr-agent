"""Local session dedupe + short conversation memory + resume flags."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


class SessionStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return {"processed": [], "sessions": {}, "meta": {}}
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if "processed" not in data:
                data["processed"] = []
            if "sessions" not in data:
                data["sessions"] = {}
            if "meta" not in data or not isinstance(data.get("meta"), dict):
                data["meta"] = {}
            return data
        except (json.JSONDecodeError, OSError):
            return {"processed": [], "sessions": {}, "meta": {}}

    def _save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
        tmp.replace(self.path)

    def is_processed(self, key: str) -> bool:
        with self._lock:
            return key in self._data["processed"]

    def mark_processed(self, key: str) -> None:
        with self._lock:
            processed: list = self._data["processed"]
            if key not in processed:
                processed.append(key)
            if len(processed) > 5000:
                self._data["processed"] = processed[-3000:]
            self._save()

    def get_history(self, session_id: str) -> list[dict]:
        with self._lock:
            raw = self._data["sessions"].get(session_id)
            if isinstance(raw, list):
                return list(raw)
            if isinstance(raw, dict):
                return list(raw.get("messages") or [])
            return []

    def append_assistant(self, session_id: str, content: str) -> None:
        with self._lock:
            hist = self._session_messages_unlocked(session_id)
            hist.append({"role": "assistant", "content": content})
            self._set_session_messages_unlocked(session_id, hist[-40:])
            self._save()

    def sync_history(self, session_id: str, messages: list[dict]) -> None:
        with self._lock:
            self._set_session_messages_unlocked(session_id, messages[-40:])
            self._save()

    def _session_messages_unlocked(self, session_id: str) -> list[dict]:
        raw = self._data["sessions"].get(session_id)
        if isinstance(raw, list):
            return list(raw)
        if isinstance(raw, dict):
            return list(raw.get("messages") or [])
        return []

    def _set_session_messages_unlocked(self, session_id: str, messages: list[dict]) -> None:
        """Store messages; preserve meta dict shape when already upgraded."""
        sessions = self._data["sessions"]
        raw = sessions.get(session_id)
        if isinstance(raw, dict):
            raw["messages"] = messages
            sessions[session_id] = raw
        else:
            # Keep legacy list shape until resume/meta is written
            sessions[session_id] = messages

    def _ensure_session_dict_unlocked(self, session_id: str) -> dict[str, Any]:
        sessions = self._data["sessions"]
        raw = sessions.get(session_id)
        if isinstance(raw, dict):
            if "messages" not in raw:
                raw["messages"] = []
            if "flags" not in raw or not isinstance(raw.get("flags"), dict):
                raw["flags"] = {}
            return raw
        messages = list(raw) if isinstance(raw, list) else []
        upgraded = {"messages": messages, "flags": {}}
        sessions[session_id] = upgraded
        return upgraded

    def get_resume_sent(self, session_id: str) -> dict[str, Any] | None:
        """Return resume marker dict if present, else None."""
        with self._lock:
            raw = self._data["sessions"].get(session_id)
            if not isinstance(raw, dict):
                return None
            if not raw.get("resumeSentAt"):
                return None
            return {
                "resumeSentAt": raw.get("resumeSentAt"),
                "resumeTrack": raw.get("resumeTrack"),
                "resumeSource": raw.get("resumeSource"),
            }

    def mark_resume_sent(
        self,
        session_id: str,
        *,
        track: str | None = None,
        source: str = "history_bootstrap",
    ) -> None:
        """Persist that attachment resume was already sent for this chat."""
        with self._lock:
            sess = self._ensure_session_dict_unlocked(session_id)
            if not sess.get("resumeSentAt"):
                sess["resumeSentAt"] = _utc_now_iso()
            if track:
                sess["resumeTrack"] = track
            sess["resumeSource"] = source
            self._save()

    def update_flags(self, session_id: str, **flags: Any) -> None:
        with self._lock:
            sess = self._ensure_session_dict_unlocked(session_id)
            merged = dict(sess.get("flags") or {})
            merged.update({k: v for k, v in flags.items() if v is not None})
            sess["flags"] = merged
            self._save()

    def set_job_track(self, session_id: str, job_track: str) -> None:
        with self._lock:
            sess = self._ensure_session_dict_unlocked(session_id)
            sess["jobTrack"] = job_track
            self._save()
