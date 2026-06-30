"""
Unit tests for the Normalization layer of the candidate transformer.
Tests success and boundary scenarios for normalize_candidate and sub-functions.
"""

import unittest
from candidate_transformer.models import (
    Candidate,
    CandidateValue,
    EducationEntry,
    ExperienceEntry,
)
from candidate_transformer.normalization import (
    normalize_candidate,
    normalize_email,
    normalize_phone,
)


class TestNormalization(unittest.TestCase):
    def test_email_normalization(self):
        email_cv = CandidateValue(
            value="  Jane.Doe@Example.Com  ",
            confidence=0.80,
            source="resume_txt",
            method="resume_regex",
        )
        normalize_email(email_cv)
        self.assertEqual(email_cv.value, "jane.doe@example.com")
        self.assertEqual(email_cv.confidence, 0.80)
        self.assertEqual(email_cv.source, "resume_txt")
        self.assertEqual(email_cv.method, "resume_regex")

    def test_phone_normalization(self):
        # Starts with +
        p1 = CandidateValue("+1 415 555 0199", 0.80, "resume_txt", "resume_regex")
        normalize_phone(p1)
        self.assertEqual(p1.value, "+14155550199")

        # Has parentheses and dashes (10 digits)
        p2 = CandidateValue("(415) 555-0199", 0.95, "recruiter_csv", "csv_direct")
        normalize_phone(p2)
        self.assertEqual(p2.value, "+14155550199")

        # Starts with 1 (11 digits)
        p3 = CandidateValue("14155550199", 0.80, "resume_txt", "resume_regex")
        normalize_phone(p3)
        self.assertEqual(p3.value, "+14155550199")

        # Verify metadata is untouched
        self.assertEqual(p3.confidence, 0.80)
        self.assertEqual(p3.source, "resume_txt")
        self.assertEqual(p3.method, "resume_regex")

    def test_candidate_date_and_skill_normalization(self):
        candidate = Candidate(
            candidate_id="cand_test",
            full_name=CandidateValue("Jane Doe", 1.0, "source", "method"),
            emails=[
                CandidateValue("  Jane@example.com  ", 0.80, "resume_txt", "resume_regex")
            ],
            phones=[
                CandidateValue(" (415) 555-0199 ", 0.80, "resume_txt", "resume_regex")
            ],
            location=None,
            links=[],
            headline=CandidateValue("   Engineer   ", 0.80, "resume_txt", "resume_inferred"),
            years_experience=None,
            skills=[
                CandidateValue("js", 0.80, "resume_txt", "resume_keyword"),
                CandidateValue("K8s", 0.80, "resume_txt", "resume_keyword"),
                CandidateValue("Postgres", 0.80, "resume_txt", "resume_keyword"),
                CandidateValue("Python", 0.80, "resume_txt", "resume_keyword"),
            ],
            experience=[
                ExperienceEntry(
                    company=CandidateValue(" Acme Corp  ", 0.80, "resume_txt", "resume_regex"),
                    title=CandidateValue("  Developer ", 0.80, "resume_txt", "resume_regex"),
                    start=CandidateValue("Jan 2021", 0.80, "resume_txt", "resume_regex"),
                    end=CandidateValue("Present", 0.80, "resume_txt", "resume_regex"),
                ),
                ExperienceEntry(
                    company=CandidateValue("Globex Inc", 0.80, "resume_txt", "resume_regex"),
                    title=CandidateValue("Engineer", 0.80, "resume_txt", "resume_regex"),
                    start=CandidateValue("Jun 2018", 0.80, "resume_txt", "resume_regex"),
                    end=CandidateValue("Dec 2020", 0.80, "resume_txt", "resume_regex"),
                ),
            ],
            education=[
                EducationEntry(
                    institution=CandidateValue("State University", 0.80, "resume_txt", "resume_regex"),
                    degree=CandidateValue("B.S. CS", 0.80, "resume_txt", "resume_regex"),
                    end=CandidateValue("2018", 0.80, "resume_txt", "resume_regex"),
                )
            ],
            overall_confidence=0.0,
        )

        normalize_candidate(candidate)

        # Emails & Phones
        self.assertEqual(candidate.emails[0].value, "jane@example.com")
        self.assertEqual(candidate.phones[0].value, "+14155550199")

        # Headline strip
        self.assertEqual(candidate.headline.value, "Engineer")

        # Skills mapping & unknown skill
        self.assertEqual(candidate.skills[0].value, "JavaScript")
        self.assertEqual(candidate.skills[1].value, "Kubernetes")
        self.assertEqual(candidate.skills[2].value, "PostgreSQL")
        self.assertEqual(candidate.skills[3].value, "Python")

        # Experience entries
        exp1 = candidate.experience[0]
        self.assertEqual(exp1.company.value, "Acme Corp")
        self.assertEqual(exp1.title.value, "Developer")
        self.assertEqual(exp1.start.value, "2021-01")
        self.assertIsNone(exp1.end.value)

        exp2 = candidate.experience[1]
        self.assertEqual(exp2.start.value, "2018-06")
        self.assertEqual(exp2.end.value, "2020-12")

        # Education entries
        edu = candidate.education[0]
        self.assertEqual(edu.end.value, "2018-01")

    def test_graceful_handling_empty_and_nones(self):
        candidate = Candidate(
            candidate_id="cand_empty",
            full_name=None,
            emails=[],
            phones=None,
            location=None,
            links=[],
            headline=None,
            years_experience=None,
            skills=[],
            experience=[],
            education=[],
            overall_confidence=0.0,
        )

        # Assert no exceptions are raised
        normalize_candidate(candidate)
        self.assertEqual(candidate.candidate_id, "cand_empty")
        self.assertEqual(candidate.emails, [])
        self.assertEqual(candidate.phones, None)


if __name__ == "__main__":
    unittest.main()
