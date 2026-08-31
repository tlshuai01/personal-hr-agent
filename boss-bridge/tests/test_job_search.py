"""Unit tests for job_search helpers (no network)."""

from __future__ import annotations

import unittest

from job_search import (
    draft_greeting,
    meets_min_salary_k,
    normalize_job_card,
    parse_salary_monthly_k,
    resolve_city,
)


class JobSearchTests(unittest.TestCase):
    def test_resolve_city(self) -> None:
        self.assertEqual(resolve_city("上海"), "101020100")
        self.assertEqual(resolve_city("101280600"), "101280600")

    def test_normalize_infers_data_track(self) -> None:
        card = normalize_job_card(
            {
                "jobName": "Flink 实时数据开发",
                "brandName": "某厂",
                "salaryDesc": "30-40K",
                "securityId": "sec1",
                "lid": "lid1",
            }
        )
        self.assertEqual(card["jobTrack"], "data-agent")
        self.assertIn("Flink", draft_greeting(card))

    def test_normalize_backend_default(self) -> None:
        card = normalize_job_card(
            {
                "jobName": "Java 后端工程师",
                "brandName": "某司",
                "securityId": "sec2",
                "salaryDesc": "20-30K",
            }
        )
        self.assertEqual(card["jobTrack"], "backend-agent")
        self.assertIn("Java/Python", draft_greeting(card))

    def test_parse_salary(self) -> None:
        self.assertEqual(parse_salary_monthly_k("20-30K"), (20.0, 30.0))
        self.assertEqual(parse_salary_monthly_k("40-70K"), (40.0, 70.0))
        self.assertEqual(parse_salary_monthly_k("50K以上"), (50.0, 50.0))
        self.assertEqual(parse_salary_monthly_k("350-400元/天"), (None, None))
        self.assertEqual(parse_salary_monthly_k("面议"), (None, None))

    def test_min_salary_20k(self) -> None:
        self.assertTrue(meets_min_salary_k("20-30K", min_k=20))
        self.assertTrue(meets_min_salary_k("40-70K", min_k=20))
        self.assertFalse(meets_min_salary_k("15-25K", min_k=20))
        self.assertFalse(meets_min_salary_k("10-15K", min_k=20))
        self.assertFalse(meets_min_salary_k("350-400元/天", min_k=20))


if __name__ == "__main__":
    unittest.main()
