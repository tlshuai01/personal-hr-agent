"""Unit tests for reply_mode / needs_reply heuristics."""

from __future__ import annotations

import unittest
from pathlib import Path
import tempfile

from main import (
    _needs_reply,
    _seed_new_message_baseline,
    _friend_dedupe_key,
)
from session_store import SessionStore


class NeedsReplyTests(unittest.TestCase):
    def test_skips_self_last_message(self) -> None:
        friend = {
            "uid": 1,
            "encryptUid": "abc",
            "lastMsg": "你好",
            "lastMessageInfo": {"fromId": 99, "showText": "你好"},
            "unreadCount": 1,
        }
        # fromId != uid → from boss in our heuristic when boss is uid... 
        # _last_message_from_self: from_id != boss_uid means NOT self when boss_uid is friend.uid
        # Actually friend.uid is the Boss (HR). fromId == boss uid → from HR → needs reply.
        # fromId != boss → from self (geek).
        self.assertFalse(_needs_reply(friend, reply_mode="all"))

    def test_unread_mode_requires_unread(self) -> None:
        friend = {
            "uid": 10,
            "encryptUid": "s1",
            "lastMsg": "方便聊聊吗",
            "lastMessageInfo": {"fromId": 10, "showText": "方便聊聊吗"},
            "unreadCount": 0,
        }
        self.assertTrue(_needs_reply(friend, reply_mode="all"))
        self.assertTrue(_needs_reply(friend, reply_mode="new"))
        self.assertFalse(_needs_reply(friend, reply_mode="unread"))

        friend["unreadCount"] = 2
        self.assertTrue(_needs_reply(friend, reply_mode="unread"))

    def test_baseline_marks_current_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SessionStore(Path(tmp) / "sessions.json")
            friends = [
                {
                    "uid": 1,
                    "encryptUid": "a",
                    "lastMsg": "旧消息",
                    "lastMessageInfo": {"fromId": 1, "showText": "旧消息"},
                },
                {
                    "uid": 2,
                    "encryptUid": "b",
                    "lastMsg": "另一条",
                    "lastMessageInfo": {"fromId": 2, "showText": "另一条"},
                },
            ]
            n = _seed_new_message_baseline(friends, store)
            self.assertEqual(n, 2)
            self.assertTrue(store.is_processed(_friend_dedupe_key(friends[0])))
            self.assertTrue(store.is_processed(_friend_dedupe_key(friends[1])))


if __name__ == "__main__":
    unittest.main()
