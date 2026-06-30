"""
Unit tests for the Merge Engine of the candidate transformer.
Tests scalar merge, list merge, complete candidate merge, and confidence calculations.
"""

import unittest
from candidate_transformer.models import (
    Candidate,
    CandidateValue,
    EducationEntry,
    ExperienceEntry,
)
from candidate_transformer.merge import (
    merge_scalar_values,
    merge_skills,
    merge_experience,
    merge_education,
    merge_candidates,
)


class TestScalarMerge(unittest.TestCase):
    def setUp(self):
        self.val_csv = CandidateValue(
            value="Jane Doe",
            confidence=0.95,
            source="recruiter_csv",
            method="csv_direct",
        )
        self.val_resume = CandidateValue(
            value="Jane Doe",
            confidence=0.80,
            source="resume_txt",
            method="resume_regex",
        )
        self.val_resume_diff = CandidateValue(
            value="John Doe",
            confidence=0.80,
            source="resume_txt",
            method="resume_regex",
        )

    def test_left_none(self):
        res = merge_scalar_values(None, self.val_csv)
        self.assertIsNotNone(res)
        self.assertEqual(res.value, "Jane Doe")
        self.assertEqual(res.confidence, 0.95)
        self.assertEqual(res.source, "recruiter_csv")
        self.assertEqual(res.method, "csv_direct")

    def test_right_none(self):
        res = merge_scalar_values(self.val_csv, None)
        self.assertIsNotNone(res)
        self.assertEqual(res.value, "Jane Doe")
        self.assertEqual(res.confidence, 0.95)

    def test_both_none(self):
        res = merge_scalar_values(None, None)
        self.assertIsNone(res)

    def test_value_is_none(self):
        none_val = CandidateValue(None, 0.95, "recruiter_csv", "csv_direct")
        res = merge_scalar_values(none_val, self.val_resume)
        self.assertIsNotNone(res)
        self.assertEqual(res.value, "Jane Doe")
        self.assertEqual(res.confidence, 0.80)
        self.assertEqual(res.source, "resume_txt")
        self.assertEqual(res.method, "resume_regex")

    def test_agreement_and_confidence_boost(self):
        res = merge_scalar_values(self.val_csv, self.val_resume)
        self.assertIsNotNone(res)
        self.assertEqual(res.value, "Jane Doe")
        self.assertEqual(res.confidence, 1.0)
        self.assertEqual(res.source, ["recruiter_csv", "resume_txt"])
        self.assertEqual(res.method, "agreed")

        val_resume_dup = CandidateValue("Jane Doe", 0.80, "resume_txt", "resume_regex")
        res2 = merge_scalar_values(self.val_resume, val_resume_dup)
        self.assertEqual(res2.confidence, 0.85)
        self.assertEqual(res2.source, "resume_txt")

    def test_disagreement_higher_confidence_wins(self):
        val_high = CandidateValue("High Conf", 0.95, "source_a", "method_a")
        val_low = CandidateValue("Low Conf", 0.80, "source_b", "method_b")

        res_a_wins = merge_scalar_values(val_high, val_low)
        self.assertEqual(res_a_wins.value, "High Conf")
        self.assertEqual(res_a_wins.confidence, 0.95)

        res_b_wins = merge_scalar_values(val_low, val_high)
        self.assertEqual(res_b_wins.value, "High Conf")
        self.assertEqual(res_b_wins.confidence, 0.95)

    def test_csv_direct_tie_breaker(self):
        val_csv_tie = CandidateValue("CSV Val", 0.80, "recruiter_csv", "csv_direct")
        val_res_tie = CandidateValue("Resume Val", 0.80, "resume_txt", "resume_regex")

        res1 = merge_scalar_values(val_csv_tie, val_res_tie)
        self.assertEqual(res1.value, "CSV Val")
        self.assertEqual(res1.method, "csv_direct")

        res2 = merge_scalar_values(val_res_tie, val_csv_tie)
        self.assertEqual(res2.value, "CSV Val")
        self.assertEqual(res2.method, "csv_direct")

    def test_tie_breaker_default(self):
        val1 = CandidateValue("Left Val", 0.80, "resume_txt", "resume_regex")
        val2 = CandidateValue("Right Val", 0.80, "resume_txt", "resume_keyword")

        res = merge_scalar_values(val1, val2)
        self.assertEqual(res.value, "Left Val")
        self.assertEqual(res.method, "resume_regex")

    def test_no_mutation(self):
        val_a = CandidateValue("Val A", 0.95, "src_a", "method_a")
        val_b = CandidateValue("Val B", 0.80, "src_b", "method_b")

        _ = merge_scalar_values(val_a, val_b)
        self.assertEqual(val_a.value, "Val A")
        self.assertEqual(val_a.confidence, 0.95)
        self.assertEqual(val_b.value, "Val B")
        self.assertEqual(val_b.confidence, 0.80)


class TestListMerge(unittest.TestCase):
    def test_skills_merge(self):
        list_a = [
            CandidateValue("Python", 0.95, "recruiter_csv", "csv_direct"),
            CandidateValue("AWS", 0.80, "resume_txt", "resume_keyword"),
        ]
        list_b = [
            CandidateValue("AWS", 0.80, "resume_txt", "resume_keyword"),
            CandidateValue("Kubernetes", 0.80, "resume_txt", "resume_keyword"),
        ]

        res = merge_skills(list_a, list_b)
        self.assertEqual(len(res), 3)
        self.assertEqual(res[0].value, "Python")
        self.assertEqual(res[1].value, "AWS")
        self.assertEqual(res[1].confidence, 0.85)
        self.assertEqual(res[2].value, "Kubernetes")

    def test_experience_merge(self):
        exp_a = [
            ExperienceEntry(
                company=CandidateValue("Acme Corp", 0.95, "recruiter_csv", "csv_direct"),
                title=CandidateValue("Developer", 0.95, "recruiter_csv", "csv_direct"),
                start=None,
                end=None,
            )
        ]

        exp_b = [
            ExperienceEntry(
                company=CandidateValue("Acme Corp", 0.80, "resume_txt", "resume_regex"),
                title=CandidateValue("Developer", 0.80, "resume_txt", "resume_regex"),
                start=CandidateValue("Jan 2021", 0.80, "resume_txt", "resume_regex"),
                end=CandidateValue("Present", 0.80, "resume_txt", "resume_regex"),
            ),
            ExperienceEntry(
                company=CandidateValue("Globex Inc", 0.80, "resume_txt", "resume_regex"),
                title=CandidateValue("Engineer", 0.80, "resume_txt", "resume_regex"),
                start=CandidateValue("Jun 2018", 0.80, "resume_txt", "resume_regex"),
                end=CandidateValue("Dec 2020", 0.80, "resume_txt", "resume_regex"),
            ),
        ]

        res = merge_experience(exp_a, exp_b)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0].company.value, "Acme Corp")
        self.assertEqual(res[0].company.confidence, 1.0)
        self.assertEqual(res[0].start.value, "Jan 2021")
        self.assertEqual(res[1].company.value, "Globex Inc")

    def test_education_merge(self):
        edu_a = [
            EducationEntry(
                institution=CandidateValue("State University", 0.95, "csv", "csv_direct"),
                degree=CandidateValue("B.S. CS", 0.95, "csv", "csv_direct"),
                end=None,
            )
        ]
        edu_b = [
            EducationEntry(
                institution=CandidateValue("State University", 0.80, "resume", "resume_regex"),
                degree=CandidateValue("B.S. CS", 0.80, "resume", "resume_regex"),
                end=CandidateValue("2018", 0.80, "resume", "resume_regex"),
            )
        ]

        res = merge_education(edu_a, edu_b)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].institution.value, "State University")
        self.assertEqual(res[0].end.value, "2018")


class TestCompleteMerge(unittest.TestCase):
    def test_merge_complete_candidates_worked_example(self):
        # candidate_a (CSV-extracted shape)
        candidate_a = Candidate(
            candidate_id="",
            full_name=CandidateValue("Jane Doe", 0.95, "recruiter_csv", "csv_direct"),
            emails=[CandidateValue("jane.doe@example.com", 0.95, "recruiter_csv", "csv_direct")],
            phones=[CandidateValue("+14155550199", 0.95, "recruiter_csv", "csv_direct")],
            location=None,
            links=[],
            headline=None,
            years_experience=None,
            skills=[],
            experience=[
                ExperienceEntry(
                    company=CandidateValue("Acme Corp", 0.95, "recruiter_csv", "csv_direct"),
                    title=CandidateValue("Senior Software Engineer", 0.95, "recruiter_csv", "csv_direct"),
                    start=None,
                    end=None,
                )
            ],
            education=[],
            overall_confidence=0.0,
        )

        # candidate_b (Resume-extracted shape)
        candidate_b = Candidate(
            candidate_id="",
            full_name=CandidateValue("Jane Doe", 0.80, "resume_txt", "resume_regex"),
            emails=[CandidateValue("jane.doe@example.com", 0.80, "resume_txt", "resume_regex")],
            phones=[CandidateValue("+14155550199", 0.80, "resume_txt", "resume_regex")],
            location=None,
            links=[],
            headline=CandidateValue("Senior Backend Engineer", 0.60, "resume_txt", "resume_inferred"),
            years_experience=CandidateValue(6, 0.60, "resume_txt", "resume_inferred"),
            skills=[
                CandidateValue("Python", 0.80, "resume_txt", "resume_keyword"),
                CandidateValue("AWS", 0.80, "resume_txt", "resume_keyword"),
                CandidateValue("Docker", 0.80, "resume_txt", "resume_keyword"),
                CandidateValue("Kubernetes", 0.80, "resume_txt", "resume_keyword"),
                CandidateValue("JavaScript", 0.80, "resume_txt", "resume_keyword"),
            ],
            experience=[
                ExperienceEntry(
                    company=CandidateValue("Acme Corp", 0.80, "resume_txt", "resume_regex"),
                    title=CandidateValue("Senior Software Engineer", 0.80, "resume_txt", "resume_regex"),
                    start=CandidateValue("2021-01", 0.80, "resume_txt", "resume_regex"),
                    end=None,
                ),
                ExperienceEntry(
                    company=CandidateValue("Globex Inc", 0.80, "resume_txt", "resume_regex"),
                    title=CandidateValue("Software Engineer", 0.80, "resume_txt", "resume_regex"),
                    start=CandidateValue("2018-06", 0.80, "resume_txt", "resume_regex"),
                    end=CandidateValue("2020-12", 0.80, "resume_txt", "resume_regex"),
                ),
            ],
            education=[
                EducationEntry(
                    institution=CandidateValue("State University", 0.80, "resume_txt", "resume_regex"),
                    degree=CandidateValue("B.S. Computer Science", 0.80, "resume_txt", "resume_regex"),
                    end=CandidateValue("2018-01", 0.80, "resume_txt", "resume_regex"),
                )
            ],
            overall_confidence=0.0,
        )

        merged = merge_candidates(candidate_a, candidate_b)

        # Assert merged CandidateValue structures & values
        self.assertEqual(merged.full_name.value, "Jane Doe")
        self.assertEqual(merged.full_name.confidence, 1.0)
        self.assertEqual(merged.full_name.method, "agreed")
        self.assertEqual(merged.full_name.source, ["recruiter_csv", "resume_txt"])

        self.assertEqual(merged.emails[0].value, "jane.doe@example.com")
        self.assertEqual(merged.emails[0].confidence, 1.0)

        self.assertEqual(merged.phones[0].value, "+14155550199")
        self.assertEqual(merged.phones[0].confidence, 1.0)

        self.assertEqual(merged.headline.value, "Senior Backend Engineer")
        self.assertEqual(merged.headline.confidence, 0.60)

        self.assertEqual(merged.years_experience.value, 6)
        self.assertEqual(merged.years_experience.confidence, 0.60)

        self.assertEqual(len(merged.skills), 5)
        self.assertEqual(merged.skills[0].value, "Python")
        self.assertEqual(merged.skills[0].confidence, 0.80)

        # Check Experience
        self.assertEqual(len(merged.experience), 2)
        exp_acme = merged.experience[0]
        self.assertEqual(exp_acme.company.value, "Acme Corp")
        self.assertEqual(exp_acme.company.confidence, 1.0)
        self.assertEqual(exp_acme.title.value, "Senior Software Engineer")
        self.assertEqual(exp_acme.title.confidence, 1.0)
        self.assertEqual(exp_acme.start.value, "2021-01")
        self.assertEqual(exp_acme.start.confidence, 0.80)
        self.assertIsNone(exp_acme.end)

        exp_globex = merged.experience[1]
        self.assertEqual(exp_globex.company.value, "Globex Inc")
        self.assertEqual(exp_globex.start.value, "2018-06")

        # Check Education
        self.assertEqual(len(merged.education), 1)
        edu = merged.education[0]
        self.assertEqual(edu.institution.value, "State University")
        self.assertEqual(edu.degree.value, "B.S. Computer Science")
        self.assertEqual(edu.end.value, "2018-01")

        # Check overall_confidence matches the computed 0.83
        self.assertEqual(merged.overall_confidence, 0.83)

        # Verify candidate_id remains empty
        self.assertEqual(merged.candidate_id, "")

        # Verify inputs are not mutated
        self.assertEqual(candidate_a.full_name.confidence, 0.95)
        self.assertEqual(candidate_b.full_name.confidence, 0.80)

    def test_merge_csv_only_with_empty(self):
        candidate_csv = Candidate(
            candidate_id="",
            full_name=CandidateValue("Jane Doe", 0.95, "recruiter_csv", "csv_direct"),
            emails=[CandidateValue("jane.doe@example.com", 0.95, "recruiter_csv", "csv_direct")],
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
        candidate_empty = Candidate(
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

        merged = merge_candidates(candidate_csv, candidate_empty)
        self.assertEqual(merged.full_name.value, "Jane Doe")
        self.assertEqual(merged.full_name.confidence, 0.95)
        self.assertEqual(merged.emails[0].value, "jane.doe@example.com")
        self.assertEqual(merged.overall_confidence, 0.95)  # (0.95 + 0.95) / 2 = 0.95

    def test_merge_resume_only_with_empty(self):
        candidate_resume = Candidate(
            candidate_id="",
            full_name=CandidateValue("Jane Doe", 0.80, "resume_txt", "resume_regex"),
            emails=[],
            phones=[],
            location=None,
            links=[],
            headline=None,
            years_experience=None,
            skills=[CandidateValue("Python", 0.80, "resume_txt", "resume_keyword")],
            experience=[],
            education=[],
            overall_confidence=0.0,
        )
        candidate_empty = Candidate(
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

        merged = merge_candidates(candidate_empty, candidate_resume)
        self.assertEqual(merged.full_name.value, "Jane Doe")
        self.assertEqual(merged.skills[0].value, "Python")
        self.assertEqual(merged.overall_confidence, 0.80)  # (0.80 + 0.80) / 2 = 0.80

    def test_merge_both_empty(self):
        cand_a = Candidate("", None, [], [], None, [], None, None, [], [], [], 0.0)
        cand_b = Candidate("", None, [], [], None, [], None, None, [], [], [], 0.0)

        merged = merge_candidates(cand_a, cand_b)
        self.assertEqual(merged.overall_confidence, 0.0)
        self.assertEqual(merged.emails, [])
        self.assertIsNone(merged.full_name)


if __name__ == "__main__":
    unittest.main()
