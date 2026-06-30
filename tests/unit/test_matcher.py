"""
Unit tests for the Candidate Matcher of the candidate transformer.
Tests matching by normalized email, CSV-only, and Resume-only outputs.
"""

import unittest
from candidate_transformer.matcher import CandidateMatcher


class TestMatcher(unittest.TestCase):
    def test_matcher_matched_and_unmatched(self):
        csv_rows = [
            {"name": "Jane Doe", "email": "Jane.Doe@example.com"},
            {"name": "John Smith", "email": "john@example.com"},
            {"name": "Only CSV", "email": "csv@example.com"},
        ]
        resumes = {
            "jane_resume.txt": (
                "jane_resume.txt",
                "Jane Doe\nCONTACT\nEmail: jane.doe@example.com",
            ),
            "john_resume.txt": (
                "john_resume.txt",
                "John Smith\nCONTACT\nEmail: john@example.com",
            ),
            "only_res_resume.txt": (
                "only_res_resume.txt",
                "Only Res\nCONTACT\nEmail: res@example.com",
            ),
        }

        matcher = CandidateMatcher()
        work_items = matcher.match(csv_rows, resumes)

        # Expected total work items:
        # 2 matched (Jane, John)
        # 1 CSV-only (Only CSV)
        # 1 Resume-only (Only Res)
        # Total = 4
        self.assertEqual(len(work_items), 4)

        # Verify matched pairs
        matched_jane = [
            item
            for item in work_items
            if item.get("csv_row")
            and item["csv_row"].get("name") == "Jane Doe"
            and item.get("resume_text")
        ]
        self.assertEqual(len(matched_jane), 1)

        # Verify CSV-only
        csv_only = [
            item
            for item in work_items
            if item.get("csv_row")
            and item["csv_row"].get("name") == "Only CSV"
            and not item.get("resume_text")
        ]
        self.assertEqual(len(csv_only), 1)

        # Verify Resume-only
        res_only = [
            item
            for item in work_items
            if not item.get("csv_row") and item.get("resume_path")
        ]
        self.assertEqual(len(res_only), 1)
        self.assertIn("Only Res", res_only[0]["resume_text"])


if __name__ == "__main__":
    unittest.main()
