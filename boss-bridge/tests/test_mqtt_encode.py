"""Unit tests for MQTT protobuf helpers (no network)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_BRIDGE = Path(__file__).resolve().parents[1]
if str(_BRIDGE) not in sys.path:
    sys.path.insert(0, str(_BRIDGE))

from mqtt_chat import build_text_message  # noqa: E402


class MqttEncodeTest(unittest.TestCase):
    def test_build_text_message_nonempty(self) -> None:
        payload = build_text_message(1, "enc-me", 2, "enc-boss", "你好")
        self.assertIsInstance(payload, bytes)
        self.assertGreater(len(payload), 10)
        self.assertIn("你好".encode("utf-8"), payload)


if __name__ == "__main__":
    unittest.main()
