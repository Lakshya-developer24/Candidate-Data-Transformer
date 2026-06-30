"""
Unit tests for the Pipeline Orchestrator of the candidate transformer.
Tests happy paths for matched, CSV-only, and Resume-only entries,
and failure handling for extraction and validation stages.
"""

import unittest
from candidate_transformer.pipeline import run_pipeline


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.csv_row = {
            "name": "Jane Doe",
            "email": "jane.doe@example.com",
            "phone": "(415) 555-0199",
            "company": "Acme Corp",
            "title": "Senior Software Engineer",
        }
        self.resume_text = """Jane Doe
Senior Backend Engineer

SUMMARY
6+ years of experience

CONTACT
jane.doe@example.com
+1 415 555 0199

SKILLS
Python, AWS, Docker, Kubernetes, JavaScript

EXPERIENCE
Acme Corp — Senior Software Engineer
Jan 2021 - Present

Globex Inc — Software Engineer
Jun 2018 - Dec 2020

EDUCATION
State University, B.S. Computer Science, 2018
"""

    def test_pipeline_matched(self):
        # CSV + Resume text
        projected = run_pipeline(
            csv_row=self.csv_row,
            resume_text=self.resume_text,
            config={"on_missing": "null"},
        )

        self.assertNotIn("reason", projected)
        self.assertEqual(projected["full_name"]["value"], "Jane Doe")
        self.assertEqual(projected["emails"][0]["value"], "jane.doe@example.com")
        self.assertEqual(projected["phones"][0]["value"], "+14155550199")

    def test_pipeline_csv_only(self):
        # CSV only
        projected = run_pipeline(
            csv_row=self.csv_row,
            config={"on_missing": "null"},
        )

        self.assertNotIn("reason", projected)
        self.assertEqual(projected["full_name"]["value"], "Jane Doe")
        self.assertEqual(projected["emails"][0]["value"], "jane.doe@example.com")

    def test_pipeline_resume_only(self):
        # Resume only
        projected = run_pipeline(
            resume_text=self.resume_text,
            config={"on_missing": "null"},
        )

        self.assertNotIn("reason", projected)
        self.assertEqual(projected["full_name"]["value"], "Jane Doe")
        self.assertEqual(projected["skills"][0]["value"], "Python")

    def test_pipeline_validation_failure(self):
        # validation error: location is missing and on_missing is "error"
        config = {
            "fields": [{"from": "full_name"}, {"from": "location"}],
            "on_missing": "error",
        }

        failure = run_pipeline(
            csv_row=self.csv_row,
            config=config,
        )

        self.assertIn("reason", failure)
        self.assertEqual(failure["stage"], "validation")
        self.assertEqual(failure["source"], "recruiter_csv")
        self.assertEqual(failure["identifier"], "Jane Doe")

    def test_pipeline_extractor_failure(self):
        # Extraction failure: CSV row missing required "name"
        bad_csv = {"email": "no.name@example.com"}

        failure = run_pipeline(
            csv_row=bad_csv,
            config={"on_missing": "null"},
        )

        self.assertIn("reason", failure)
        self.assertEqual(failure["stage"], "extraction")
        self.assertEqual(failure["source"], "recruiter_csv")
        self.assertEqual(failure["identifier"], "no.name@example.com")


if __name__ == "__main__":
    unittest.main()
