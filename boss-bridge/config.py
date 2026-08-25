"""Configuration for Boss Bridge."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

_BRIDGE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _BRIDGE_DIR.parent


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


@dataclass
class BridgeConfig:
    phase: str = "c1"
    boss_cli_bin: str = "boss"
    boss_cli_timeout_sec: int = 60
    agent_base_url: str = "http://127.0.0.1:3000"
    boss_bridge_secret: str = ""
    agent_timeout_sec: int = 120
    poll_interval_sec: int = 25
    send_delay_sec: float = 3.0
    history_limit: int = 20
    log_level: str = "INFO"
    session_store_path: Path = field(default_factory=lambda: _BRIDGE_DIR / "data" / "sessions.json")


def load_config() -> BridgeConfig:
    load_dotenv(_BRIDGE_DIR / ".env")
    load_dotenv(_REPO_ROOT / ".env.local")
    load_dotenv(_REPO_ROOT / ".env")

    store = _env("SESSION_STORE_PATH")
    store_path = Path(store) if store else _BRIDGE_DIR / "data" / "sessions.json"

    return BridgeConfig(
        boss_cli_bin=_env("BOSS_CLI_BIN", "boss"),
        boss_cli_timeout_sec=int(_env("BOSS_CLI_TIMEOUT_SEC", "60")),
        agent_base_url=_env("AGENT_BASE_URL", "http://127.0.0.1:3000").rstrip("/"),
        boss_bridge_secret=_env("BOSS_BRIDGE_SECRET") or _env("BRIDGE_SECRET"),
        agent_timeout_sec=int(_env("AGENT_TIMEOUT_SEC", "120")),
        poll_interval_sec=int(_env("POLL_INTERVAL_SEC", "25")),
        send_delay_sec=float(_env("SEND_DELAY_SEC", "3")),
        history_limit=int(_env("HISTORY_LIMIT", "20")),
        log_level=_env("LOG_LEVEL", "INFO"),
        session_store_path=store_path,
    )
