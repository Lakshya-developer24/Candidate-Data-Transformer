"""
Unit tests for the ID Generator of the candidate transformer.
Tests primary email hashing and various fallbacks.
"""

import unittest
from candidate_transformer.models import Candidate, CandidateValue
from candidate_transformer.id_generator import generate_candidate_id, sha256


class TestIdGenerator(unittest.TestCase):
    def test_id_from_email(self):
        cand = Candidate(
            candidate_id="",
            full_name=CandidateValue("Jane Doe", 1.0, "csv", "csv_direct"),
            emails=[
                CandidateValue("jane.doe@example.com", 1.0, "csv", "csv_direct")
            ],
            phones=[CandidateValue("+14155550199", 1.0, "csv", "csv_direct")],
            location=None,
            links=[],
            headline=None,
            years_experience=None,
            skills=[],
            experience=[],
            education=[],
            overall_confidence=0.0,
        )
        expected = "cand_" + sha256("jane.doe@example.com")[:12]
        self.assertEqual(generate_candidate_id(cand), expected)

    def test_id_fallback_name_phone(self):
        cand = Candidate(
            candidate_id="",
            full_name=CandidateValue("Jane Doe", 1.0, "csv", "csv_direct"),
            emails=[],  # no email
            phones=[CandidateValue("+14155550199", 1.0, "csv", "csv_direct")],
            location=None,
            links=[],
            headline=None,
            years_experience=None,
            skills=[],
            experience=[],
            education=[],
            overall_confidence=0.0,
        )
        expected = "cand_" + sha256("jane doe+14155550199")[:12]
        self.assertEqual(generate_candidate_id(cand), expected)

    def test_id_fallback_filename_index(self):
        cand = Candidate(
            candidate_id="",
            full_name=None,  # no name/phone
            emails=[],
            phones=[],
            location=None,
            links=[],
            headline=None,
            years_experience=None,
            skills=[],
            experience=[],
            education=[],
            overall_confidence=0.0,
        )
        expected = "cand_" + sha256("recruiter_export.csv" + "5")[:12]
        self.assertEqual(
            generate_candidate_id(cand, "recruiter_export.csv", 5), expected
        )

    def test_id_fallback_last_resort(self):
        cand = Candidate(
            candidate_id="",
            full_name=None,
            emails=[],
            phones=[],
            location=None,
            links=[],
            headline=None,
            years_experience=None,
            skills=[],
            experience=[],
            education=[],
            overall_confidence=0.0,
        )
        # Should deterministically fallback to row_index (or 0)
        expected = "cand_" + sha256("last_resort_0")[:12]
        self.assertEqual(generate_candidate_id(cand), expected)


if __name__ == "__main__":
    unittest.main()
