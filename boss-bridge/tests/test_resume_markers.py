"""Unit tests for resume request / sent heuristics (no live Boss calls)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_BRIDGE = Path(__file__).resolve().parents[1]
if str(_BRIDGE) not in sys.path:
    sys.path.insert(0, str(_BRIDGE))

from boss_transport import (  # noqa: E402
    extract_encrypt_resume_ids,
    find_pending_resume_request,
    history_indicates_resume_sent,
)


def _request_card(*, operated: bool = False, mid: int = 1) -> dict:
    return {
        "mid": mid,
        "from": {"uid": 9001},
        "body": {
            "dialog": {
                "text": "我想要一份您的附件简历",
                "operated": operated,
                "buttons": [
                    {
                        "text": "同意",
                        "url": "bosszp://bosszhipin.app/openwith?type=sendaction&uid=9001&aid=38",
                    },
                    {"text": "拒绝", "url": "bosszp://bosszhipin.app/openwith?type=sendaction&uid=9001&aid=39"},
                ],
            }
        },
    }


def _sent_geek_msg() -> dict:
    return {
        "mid": 2,
        "body": {
            "action": {"aid": 38},
            "hyperLink": {
                "extraJson": '{"encryptResumeId":"abc~resume1","type":"attach-resume"}'
            },
        },
    }


class ResumeMarkersTest(unittest.TestCase):
    def test_request_only_is_not_sent(self) -> None:
        self.assertFalse(history_indicates_resume_sent([_request_card()]))

    def test_aid38_counts_as_sent(self) -> None:
        self.assertTrue(history_indicates_resume_sent([_sent_geek_msg()]))

    def test_viewed_marker_counts_as_sent(self) -> None:
        raw = [{"body": {"text": "对方已查看了您的附件简历"}}]
        self.assertTrue(history_indicates_resume_sent(raw))

    def test_find_pending_agree_url(self) -> None:
        pending = find_pending_resume_request([_request_card(mid=42)])
        assert pending is not None
        self.assertEqual(pending["mid"], 42)
        self.assertEqual(pending["bossUid"], 9001)
        self.assertIn("aid=38", pending["agreeUrl"])

    def test_find_pending_skips_operated(self) -> None:
        self.assertIsNone(
            find_pending_resume_request([_request_card(operated=True)])
        )

    def test_extract_encrypt_resume_ids(self) -> None:
        ids = extract_encrypt_resume_ids([_sent_geek_msg()])
        self.assertIn("abc~resume1", ids)


if __name__ == "__main__":
    unittest.main()
