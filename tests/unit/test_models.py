"""
Unit tests for candidate transformer models.
Verifies that all models can be imported and instantiated with standard types.
"""

import unittest
from candidate_transformer.models import (
    CandidateValue,
    ExperienceEntry,
    EducationEntry,
    Candidate,
)


class TestCandidateModels(unittest.TestCase):
    def test_candidate_value_instantiation(self):
        val = CandidateValue(
            value="John Doe",
            confidence=0.95,
            source="resume",
            method="regex"
        )
        self.assertEqual(val.value, "John Doe")
        self.assertEqual(val.confidence, 0.95)
        self.assertEqual(val.source, "resume")
        self.assertEqual(val.method, "regex")

    def test_experience_entry_instantiation(self):
        comp = CandidateValue("Google", 1.0, "resume", "ner")
        title = CandidateValue("Software Engineer", 1.0, "resume", "ner")
        start = CandidateValue("2020-01", 0.9, "resume", "regex")
        end = CandidateValue("2023-01", 0.9, "resume", "regex")

        exp = ExperienceEntry(
            company=comp,
            title=title,
            start=start,
            end=end
        )
        self.assertEqual(exp.company.value, "Google")
        self.assertEqual(exp.title.value, "Software Engineer")

    def test_education_entry_instantiation(self):
        inst = CandidateValue("Stanford University", 1.0, "resume", "ner")
        deg = CandidateValue("B.S. Computer Science", 1.0, "resume", "ner")
        end = CandidateValue("2020-06", 0.9, "resume", "regex")

        edu = EducationEntry(
            institution=inst,
            degree=deg,
            end=end
        )
        self.assertEqual(edu.institution.value, "Stanford University")
        self.assertEqual(edu.degree.value, "B.S. Computer Science")

    def test_candidate_instantiation(self):
        name = CandidateValue("John Doe", 0.95, "resume", "regex")
        emails = [CandidateValue("john.doe@example.com", 1.0, "resume", "regex")]
        phones = [CandidateValue("+15555555555", 1.0, "resume", "regex")]
        
        cand = Candidate(
            candidate_id="uuid-1234",
            full_name=name,
            emails=emails,
            phones=phones
        )
        self.assertEqual(cand.candidate_id, "uuid-1234")
        self.assertEqual(cand.full_name.value, "John Doe")
        self.assertEqual(len(cand.emails), 1)
        self.assertEqual(cand.emails[0].value, "john.doe@example.com")


if __name__ == "__main__":
    unittest.main()
