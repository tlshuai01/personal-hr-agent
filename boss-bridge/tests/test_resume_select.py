"""Unit tests for JD/track resume selection."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_BRIDGE = Path(__file__).resolve().parents[1]
if str(_BRIDGE) not in sys.path:
    sys.path.insert(0, str(_BRIDGE))

from resume_select import (  # noqa: E402
    infer_job_track,
    resolve_attachment,
    wants_english_resume,
)


class ResumeSelectTest(unittest.TestCase):
    def test_backend_default(self) -> None:
        self.assertEqual(infer_job_track("高级后端开发工程师"), "backend-agent")

    def test_data_from_job(self) -> None:
        self.assertEqual(infer_job_track("大数据开发工程师"), "data-agent")

    def test_hr_title_ignored_when_job_present(self) -> None:
        # jobName carries signal; HR title alone should not force data
        self.assertEqual(
            infer_job_track("高级招聘HR", "软通动力正在诚聘高级后端开发工程师"),
            "backend-agent",
        )

    def test_english_only_explicit(self) -> None:
        self.assertFalse(wants_english_resume("外企长期项目，可以聊聊吗？"))
        self.assertTrue(wants_english_resume("方便发一份英文简历吗"))

    def test_resolve_backend_zh(self) -> None:
        a = resolve_attachment(track="backend-agent", english=False)
        self.assertEqual(a.lang, "zh")
        self.assertEqual(a.track, "backend-agent")
        self.assertIn("后端", a.name)

    def test_resolve_data_zh(self) -> None:
        a = resolve_attachment(track="data-agent", english=False)
        self.assertEqual(a.track, "data-agent")
        self.assertIn("数据", a.name)

    def test_resolve_backend_en(self) -> None:
        a = resolve_attachment(track="backend-agent", english=True)
        self.assertEqual(a.lang, "en")
        self.assertIn("en", a.name.lower())


if __name__ == "__main__":
    unittest.main()
