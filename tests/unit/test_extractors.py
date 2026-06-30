"""
Unit tests for the Extractor layer of the candidate transformer.
Tests success and error scenarios for CSVExtractor and ResumeExtractor.
"""

import unittest
from candidate_transformer.extractors.csv_extractor import CSVExtractor
from candidate_transformer.extractors.resume_extractor import ResumeExtractor


class TestCSVExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = CSVExtractor()

    def test_csv_extractor_complete_row(self):
        row = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "+14155550199",
            "company": "Acme Corp",
            "title": "Senior Software Engineer",
        }
        cand = self.extractor.extract(row)

        self.assertEqual(cand.full_name.value, "Jane Doe")
        self.assertEqual(cand.full_name.confidence, 0.95)
        self.assertEqual(cand.full_name.source, "recruiter_csv")
        self.assertEqual(cand.full_name.method, "csv_direct")

        self.assertEqual(len(cand.emails), 1)
        self.assertEqual(cand.emails[0].value, "jane@example.com")
        self.assertEqual(cand.emails[0].confidence, 0.95)
        self.assertEqual(cand.emails[0].source, "recruiter_csv")
        self.assertEqual(cand.emails[0].method, "csv_direct")

        self.assertEqual(len(cand.phones), 1)
        self.assertEqual(cand.phones[0].value, "+14155550199")

        self.assertEqual(len(cand.experience), 1)
        exp = cand.experience[0]
        self.assertEqual(exp.company.value, "Acme Corp")
        self.assertEqual(exp.company.confidence, 0.95)
        self.assertEqual(exp.title.value, "Senior Software Engineer")
        self.assertEqual(exp.title.confidence, 0.95)
        self.assertIsNone(exp.start)
        self.assertIsNone(exp.end)

    def test_csv_extractor_missing_optional_fields(self):
        row = {
            "name": "Jane Doe",
            # email, phone, company, title are missing from dictionary
        }
        cand = self.extractor.extract(row)

        self.assertEqual(cand.full_name.value, "Jane Doe")
        self.assertEqual(cand.emails, [])
        self.assertEqual(cand.phones, [])
        self.assertEqual(cand.experience, [])

    def test_csv_extractor_empty_optional_fields(self):
        row = {
            "name": "Jane Doe",
            "email": "",
            "phone": "  ",
            "company": "",
            "title": "   ",
        }
        cand = self.extractor.extract(row)

        self.assertEqual(cand.full_name.value, "Jane Doe")
        self.assertEqual(cand.emails, [])
        self.assertEqual(cand.phones, [])
        self.assertEqual(cand.experience, [])

    def test_csv_extractor_missing_name_error(self):
        row = {
            "email": "jane@example.com",
        }
        with self.assertRaises(ValueError):
            self.extractor.extract(row)

    def test_csv_extractor_empty_name_error(self):
        row = {
            "name": "   ",
            "email": "jane@example.com",
        }
        with self.assertRaises(ValueError):
            self.extractor.extract(row)


class TestResumeExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = ResumeExtractor()

    def test_resume_extractor_worked_example_happy_path(self):
        resume_text = """Jane Doe
Senior Backend Engineer

SUMMARY
Backend engineer with 6 years of experience building distributed systems.

SKILLS
Python, AWS, Docker, Kubernetes, JS

EXPERIENCE
Acme Corp — Senior Software Engineer
Jan 2021 - Present

Globex Inc — Software Engineer
Jun 2018 - Dec 2020

EDUCATION
B.S. Computer Science, State University, 2018

CONTACT
jane.doe@example.com
+1 415 555 0199
"""
        cand = self.extractor.extract_from_text(resume_text)

        # Name & Headline
        self.assertEqual(cand.full_name.value, "Jane Doe")
        self.assertEqual(cand.full_name.confidence, 0.80)
        self.assertEqual(cand.full_name.method, "resume_regex")
        self.assertEqual(cand.full_name.source, "resume_txt")

        self.assertIsNotNone(cand.headline)
        self.assertEqual(cand.headline.value, "Senior Backend Engineer")
        self.assertEqual(cand.headline.confidence, 0.60)
        self.assertEqual(cand.headline.method, "resume_inferred")

        # Years of experience
        self.assertIsNotNone(cand.years_experience)
        self.assertEqual(cand.years_experience.value, 6)
        self.assertEqual(cand.years_experience.confidence, 0.60)
        self.assertEqual(cand.years_experience.method, "resume_inferred")

        # Emails & Phones
        self.assertEqual(len(cand.emails), 1)
        self.assertEqual(cand.emails[0].value, "jane.doe@example.com")
        self.assertEqual(cand.emails[0].confidence, 0.80)
        self.assertEqual(cand.emails[0].method, "resume_regex")

        self.assertEqual(len(cand.phones), 1)
        self.assertEqual(cand.phones[0].value, "+1 415 555 0199")
        self.assertEqual(cand.phones[0].confidence, 0.80)
        self.assertEqual(cand.phones[0].method, "resume_regex")

        # Skills
        expected_skills = ["Python", "AWS", "Docker", "Kubernetes", "JS"]
        extracted_skills = [s.value for s in cand.skills]
        self.assertEqual(extracted_skills, expected_skills)
        for skill_val in cand.skills:
            self.assertEqual(skill_val.confidence, 0.80)
            self.assertEqual(skill_val.method, "resume_keyword")

        # Experience
        self.assertEqual(len(cand.experience), 2)
        
        # Acme Corp
        exp1 = cand.experience[0]
        self.assertEqual(exp1.company.value, "Acme Corp")
        self.assertEqual(exp1.title.value, "Senior Software Engineer")
        self.assertEqual(exp1.start.value, "Jan 2021")
        self.assertEqual(exp1.end.value, "Present")
        for cv in [exp1.company, exp1.title, exp1.start, exp1.end]:
            self.assertEqual(cv.confidence, 0.80)
            self.assertEqual(cv.method, "resume_regex")

        # Globex Inc
        exp2 = cand.experience[1]
        self.assertEqual(exp2.company.value, "Globex Inc")
        self.assertEqual(exp2.title.value, "Software Engineer")
        self.assertEqual(exp2.start.value, "Jun 2018")
        self.assertEqual(exp2.end.value, "Dec 2020")

        # Education
        self.assertEqual(len(cand.education), 1)
        edu = cand.education[0]
        self.assertEqual(edu.institution.value, "State University")
        self.assertEqual(edu.degree.value, "B.S. Computer Science")
        self.assertEqual(edu.end.value, "2018")
        for cv in [edu.institution, edu.degree, edu.end]:
            self.assertEqual(cv.confidence, 0.80)
            self.assertEqual(cv.method, "resume_regex")

    def test_resume_extractor_missing_sections(self):
        resume_text = """John Smith

EXPERIENCE
Acme Corp — Engineer
Jan 2020 - Present
"""
        cand = self.extractor.extract_from_text(resume_text)
        self.assertEqual(cand.full_name.value, "John Smith")
        self.assertEqual(cand.headline, None)
        self.assertEqual(cand.years_experience, None)
        self.assertEqual(cand.emails, [])
        self.assertEqual(cand.phones, [])
        self.assertEqual(cand.skills, [])
        self.assertEqual(cand.education, [])
        self.assertEqual(len(cand.experience), 1)

    def test_resume_extractor_missing_contact_section(self):
        resume_text = """Jane Smith

SKILLS
Python
"""
        cand = self.extractor.extract_from_text(resume_text)
        self.assertEqual(cand.emails, [])
        self.assertEqual(cand.phones, [])

    def test_resume_extractor_missing_skills_section(self):
        resume_text = """Jane Smith

CONTACT
jane@example.com
"""
        cand = self.extractor.extract_from_text(resume_text)
        self.assertEqual(cand.skills, [])

    def test_resume_extractor_missing_education_section(self):
        resume_text = """Jane Smith

CONTACT
jane@example.com
"""
        cand = self.extractor.extract_from_text(resume_text)
        self.assertEqual(cand.education, [])

    def test_resume_extractor_empty_resume(self):
        with self.assertRaises(ValueError):
            self.extractor.extract_from_text("")

    def test_resume_extractor_whitespace_only(self):
        with self.assertRaises(ValueError):
            self.extractor.extract_from_text("   \n   ")

    def test_resume_extractor_only_name(self):
        resume_text = "Jane Smith"
        cand = self.extractor.extract_from_text(resume_text)

        self.assertEqual(cand.full_name.value, "Jane Smith")
        self.assertEqual(cand.headline, None)
        self.assertEqual(cand.years_experience, None)
        self.assertEqual(cand.emails, [])
        self.assertEqual(cand.phones, [])
        self.assertEqual(cand.skills, [])
        self.assertEqual(cand.experience, [])
        self.assertEqual(cand.education, [])


if __name__ == "__main__":
    unittest.main()
