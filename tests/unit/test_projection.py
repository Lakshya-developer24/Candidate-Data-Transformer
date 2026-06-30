"""
Unit tests for the Projection Engine of the candidate transformer.
Tests path resolution, metadata configuration toggles, and missing-value rules.
"""

import unittest
from candidate_transformer.models import (
    Candidate,
    CandidateValue,
    EducationEntry,
    ExperienceEntry,
)
from candidate_transformer.projection import project_candidate


class TestProjection(unittest.TestCase):
    def setUp(self):
        self.candidate = Candidate(
            candidate_id="cand_1234",
            full_name=CandidateValue("Jane Doe", 1.0, "csv", "csv_direct"),
            emails=[
                CandidateValue("jane.doe@example.com", 0.95, "csv", "csv_direct")
            ],
            phones=[CandidateValue("+14155550199", 0.80, "resume", "resume_regex")],
            location=None,
            links=[],
            headline=CandidateValue("Engineer", 0.60, "resume", "resume_inferred"),
            years_experience=None,
            skills=[
                CandidateValue("Python", 0.80, "resume", "resume_keyword"),
                CandidateValue("AWS", 0.80, "resume", "resume_keyword"),
            ],
            experience=[
                ExperienceEntry(
                    company=CandidateValue("Acme Corp", 1.0, "csv", "csv_direct"),
                    title=CandidateValue("Developer", 1.0, "csv", "csv_direct"),
                    start=CandidateValue("2021-01", 0.80, "resume", "resume_regex"),
                    end=None,
                )
            ],
            education=[
                EducationEntry(
                    institution=CandidateValue("State U", 0.80, "resume", "resume_regex"),
                    degree=CandidateValue("B.S.", 0.80, "resume", "resume_regex"),
                    end=CandidateValue("2018-01", 0.80, "resume", "resume_regex"),
                )
            ],
            overall_confidence=0.85,
        )

    def test_default_projection(self):
        # Default selects all fields, including confidence and provenance, on_missing null
        projected = project_candidate(self.candidate)

        self.assertEqual(projected["candidate_id"], "cand_1234")
        self.assertEqual(projected["overall_confidence"], 0.85)

        self.assertEqual(projected["full_name"]["value"], "Jane Doe")
        self.assertEqual(projected["full_name"]["confidence"], 1.0)
        self.assertEqual(projected["full_name"]["source"], "csv")

        self.assertEqual(projected["emails"][0]["value"], "jane.doe@example.com")
        self.assertEqual(projected["phones"][0]["value"], "+14155550199")

        # location is None -> null
        self.assertIsNone(projected["location"])

        # skills list
        self.assertEqual(len(projected["skills"]), 2)
        self.assertEqual(projected["skills"][0]["value"], "Python")

        # Nested experience end is None -> null
        self.assertIsNone(projected["experience"][0]["end"])

    def test_renamed_fields(self):
        config = {
            "fields": [
                {"from": "full_name", "to": "name"},
                {"from": "headline", "to": "title_headline"},
            ],
            "on_missing": "null",
        }
        projected = project_candidate(self.candidate, config)

        self.assertEqual(projected["candidate_id"], "cand_1234")
        self.assertEqual(projected["name"]["value"], "Jane Doe")
        self.assertEqual(projected["title_headline"]["value"], "Engineer")
        self.assertNotIn("full_name", projected)

    def test_indexed_paths(self):
        config = {
            "fields": [
                {"from": "emails[0]", "to": "primary_email"},
                {"from": "phones[0]", "to": "primary_phone"},
            ]
        }
        projected = project_candidate(self.candidate, config)
        self.assertEqual(projected["primary_email"]["value"], "jane.doe@example.com")
        self.assertEqual(projected["primary_phone"]["value"], "+14155550199")

    def test_skills_paths(self):
        config_val = {
            "fields": [{"from": "skills[].value", "to": "skills_list"}]
        }
        projected_val = project_candidate(self.candidate, config_val)
        self.assertEqual(projected_val["skills_list"][0]["value"], "Python")

        config_name = {
            "fields": [{"from": "skills[].name", "to": "skills_list"}]
        }
        projected_name = project_candidate(self.candidate, config_name)
        self.assertEqual(projected_name["skills_list"][0]["value"], "Python")

    def test_nested_sub_fields_projection(self):
        config = {
            "fields": [
                {"from": "experience[].company", "to": "employers"},
                {"from": "education[].institution", "to": "schools"},
            ]
        }
        projected = project_candidate(self.candidate, config)
        self.assertEqual(projected["employers"][0]["value"], "Acme Corp")
        self.assertEqual(projected["schools"][0]["value"], "State U")

    def test_metadata_toggles_include_confidence_false(self):
        config = {
            "fields": [{"from": "full_name"}],
            "include_confidence": False,
            "include_provenance": True,
        }
        projected = project_candidate(self.candidate, config)
        self.assertEqual(projected["full_name"]["value"], "Jane Doe")
        self.assertNotIn("confidence", projected["full_name"])
        self.assertEqual(projected["full_name"]["source"], "csv")

    def test_metadata_toggles_include_provenance_false(self):
        config = {
            "fields": [{"from": "full_name"}],
            "include_confidence": True,
            "include_provenance": False,
        }
        projected = project_candidate(self.candidate, config)
        self.assertEqual(projected["full_name"]["value"], "Jane Doe")
        self.assertEqual(projected["full_name"]["confidence"], 1.0)
        self.assertNotIn("source", projected["full_name"])
        self.assertNotIn("method", projected["full_name"])

    def test_on_missing_omit(self):
        config = {
            "fields": [
                {"from": "full_name"},
                {"from": "location"},  # is None
            ],
            "on_missing": "omit",
        }
        projected = project_candidate(self.candidate, config)
        self.assertIn("full_name", projected)
        self.assertNotIn("location", projected)

    def test_on_missing_error_sentinel(self):
        config = {
            "fields": [
                {"from": "location"},  # is None
            ],
            "on_missing": "error",
        }
        # Verify it does not raise
        projected = project_candidate(self.candidate, config)
        self.assertEqual(projected["location"]["__missing_error__"], True)
        self.assertEqual(projected["location"]["field"], "location")

    def test_candidate_not_mutated(self):
        config = {
            "fields": [{"from": "full_name"}],
            "include_confidence": False,
            "include_provenance": False,
        }
        _ = project_candidate(self.candidate, config)

        # Verify candidate values and confidence/provenance are untouched
        self.assertEqual(self.candidate.full_name.value, "Jane Doe")
        self.assertEqual(self.candidate.full_name.confidence, 1.0)
        self.assertEqual(self.candidate.full_name.source, "csv")


if __name__ == "__main__":
    unittest.main()
