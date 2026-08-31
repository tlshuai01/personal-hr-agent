"""Tests for greet_config loading and filters."""

from __future__ import annotations

import unittest
from datetime import datetime, time

from greet_config import (
    contains_skip_keyword,
    is_within_active_hours,
    load_greet_config,
)
from job_search import job_text_blob, meets_min_salary_k


class GreetConfigTests(unittest.TestCase):
    def test_load_defaults_from_repo_file(self) -> None:
        cfg = load_greet_config()
        self.assertGreaterEqual(cfg.min_salary_k, 20)
        self.assertTrue(any("实习" in k for k in cfg.skip_keywords))
        self.assertEqual(cfg.active_start, time(9, 0))
        self.assertEqual(cfg.active_end, time(18, 0))

    def test_active_hours(self) -> None:
        cfg = load_greet_config()
        self.assertTrue(
            is_within_active_hours(cfg, datetime(2026, 9, 1, 10, 0))
        )
        self.assertFalse(
            is_within_active_hours(cfg, datetime(2026, 9, 1, 8, 59))
        )
        self.assertFalse(
            is_within_active_hours(cfg, datetime(2026, 9, 1, 18, 0))
        )

    def test_skip_keywords(self) -> None:
        self.assertEqual(contains_skip_keyword("日结兼职", ["日结", "实习"]), "日结")
        self.assertIsNone(contains_skip_keyword("Java 后端", ["日结", "实习"]))

    def test_job_blob_skip(self) -> None:
        job = {"jobName": "Java 实习", "brandName": "X", "salaryDesc": "20-30K"}
        hit = contains_skip_keyword(job_text_blob(job), ["实习"])
        self.assertEqual(hit, "实习")
        self.assertTrue(meets_min_salary_k("20-30K", min_k=20))


if __name__ == "__main__":
    unittest.main()
