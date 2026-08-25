"""Call personal-hr-agent internal reply API."""

from __future__ import annotations

import httpx


class AgentClient:
    def __init__(self, base_url: str, bridge_secret: str, timeout_sec: int = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.bridge_secret = bridge_secret
        self.timeout = timeout_sec

    def request_reply(
        self,
        *,
        session_id: str,
        messages: list[dict],
        meta: dict | None = None,
    ) -> dict:
        if not self.bridge_secret:
            raise RuntimeError("BOSS_BRIDGE_SECRET is not set")

        payload = {
            "channel": "boss",
            "sessionId": session_id,
            "messages": messages,
            "meta": meta or {},
        }
        headers = {"x-bridge-secret": self.bridge_secret, "Content-Type": "application/json"}

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.base_url}/api/internal/reply", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                raise RuntimeError(data.get("error") or "agent returned not ok")
            return data
