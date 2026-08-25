"""Local session dedupe + short conversation memory."""

from __future__ import annotations

import json
import threading
from pathlib import Path


class SessionStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return {"processed": [], "sessions": {}}
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if "processed" not in data:
                data["processed"] = []
            if "sessions" not in data:
                data["sessions"] = {}
            return data
        except (json.JSONDecodeError, OSError):
            return {"processed": [], "sessions": {}}

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
            return list(self._data["sessions"].get(session_id, []))

    def append_assistant(self, session_id: str, content: str) -> None:
        with self._lock:
            sessions = self._data["sessions"]
            hist = list(sessions.get(session_id, []))
            hist.append({"role": "assistant", "content": content})
            sessions[session_id] = hist[-40:]
            self._save()

    def sync_history(self, session_id: str, messages: list[dict]) -> None:
        with self._lock:
            self._data["sessions"][session_id] = messages[-40:]
            self._save()
