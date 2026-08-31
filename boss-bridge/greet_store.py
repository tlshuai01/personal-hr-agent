"""Persist greeted job securityIds to avoid repeat greetings."""

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


class GreetStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"greeted": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data.get("greeted"), dict):
                data["greeted"] = {}
            return data
        except (json.JSONDecodeError, OSError):
            return {"greeted": {}}

    def _save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def has_greeted(self, security_id: str) -> bool:
        with self._lock:
            return security_id in self._data["greeted"]

    def mark_greeted(
        self,
        security_id: str,
        *,
        job_name: str = "",
        brand: str = "",
        track: str = "",
        source: str = "search",
    ) -> None:
        with self._lock:
            self._data["greeted"][security_id] = {
                "at": _utc_now_iso(),
                "jobName": job_name,
                "brandName": brand,
                "track": track,
                "source": source,
            }
            # cap size
            keys = list(self._data["greeted"].keys())
            if len(keys) > 3000:
                for k in keys[: len(keys) - 2000]:
                    self._data["greeted"].pop(k, None)
            self._save()
