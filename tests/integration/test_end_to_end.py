"""
Integration tests for the candidate transformer tool.
Validates end-to-end CLI workflow, reader loading, matching, pipeline processing,
output JSON generation, and failure isolation.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from candidate_transformer.cli import main


class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        # Create temporary working directory for input and output files
        self.test_dir = tempfile.mkdtemp()

        # 1. Create a mock CSV file
        self.csv_path = os.path.join(self.test_dir, "recruiter.csv")
        csv_content = (
            "name,email,phone,company,title\n"
            "Jane Doe,jane.doe@example.com,(415) 555-0199,Acme Corp,Senior Software Engineer\n"
            "Only CSV,csv@example.com,,Globex Inc,Manager\n"
            ",bad@example.com,,,\n"  # Missing name -> extraction failure
        )
        with open(self.csv_path, "w", encoding="utf-8") as f:
            f.write(csv_content)

        # 2. Create resumes directory and text files
        self.resumes_dir = os.path.join(self.test_dir, "resumes")
        os.makedirs(self.resumes_dir)

        self.jane_resume_path = os.path.join(self.resumes_dir, "jane_resume.txt")
        jane_content = """Jane Doe
CONTACT
Email: jane.doe@example.com
Phone: +1 415 555 0199

SUMMARY
6+ years of experience

SKILLS
Python, AWS

EXPERIENCE
Acme Corp — Senior Software Engineer
Jan 2021 - Present
"""
        with open(self.jane_resume_path, "w", encoding="utf-8") as f:
            f.write(jane_content)

        self.resume_only_path = os.path.join(
            self.resumes_dir, "only_res_resume.txt"
        )
        res_content = """Only Res
CONTACT
Email: res@example.com

SKILLS
Go, Kubernetes
"""
        with open(self.resume_only_path, "w", encoding="utf-8") as f:
            f.write(res_content)

        # 3. Create output directory
        self.out_dir = os.path.join(self.test_dir, "output")

        # 4. Create a config file
        self.config_path = os.path.join(self.test_dir, "config.json")
        config_data = {
            "include_confidence": True,
            "include_provenance": True,
            "on_missing": "null",
            "fields": [
                {"from": "full_name", "to": "name"},
                {"from": "emails[0]", "to": "email"},
                {"from": "phones[0]", "to": "phone"},
                {"from": "skills"},
            ],
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_complete_cli_workflow(self):
        # Build sys.argv mock arguments
        test_args = [
            "candidate-transformer",
            "--csv",
            self.csv_path,
            "--resumes",
            self.resumes_dir,
            "--config",
            self.config_path,
            "--out",
            self.out_dir,
        ]

        with patch.object(sys, "argv", test_args):
            with patch("sys.stdout") as mock_stdout:
                main()

                # Verify printed summary line
                # Expect exactly one print call from main() on success
                self.assertTrue(mock_stdout.write.called)
                written_lines = "".join(
                    [call.args[0] for call in mock_stdout.write.call_args_list]
                )
                self.assertIn("Processed 4 candidates:", written_lines)
                self.assertIn("3 succeeded", written_lines)
                self.assertIn("1 failed", written_lines)

        # Verify output files existence
        profiles_json_path = os.path.join(self.out_dir, "profiles.json")
        failed_json_path = os.path.join(self.out_dir, "failed_candidates.json")

        self.assertTrue(os.path.exists(profiles_json_path))
        self.assertTrue(os.path.exists(failed_json_path))

        # Check profiles.json content
        with open(profiles_json_path, "r", encoding="utf-8") as f:
            profiles = json.load(f)

        # Expected successful profiles: Jane Doe (matched), Only CSV, Only Res
        self.assertEqual(len(profiles), 3)

        # Jane Doe checks (matched pair)
        jane = [p for p in profiles if p.get("name", {}).get("value") == "Jane Doe"][0]
        self.assertEqual(jane["email"]["value"], "jane.doe@example.com")
        self.assertEqual(jane["phone"]["value"], "+14155550199")
        self.assertIn("Python", [sk["value"] for sk in jane["skills"]])
        self.assertTrue(jane["candidate_id"].startswith("cand_"))

        # Only CSV checks
        only_csv = [
            p for p in profiles if p.get("name", {}).get("value") == "Only CSV"
        ][0]
        self.assertEqual(only_csv["email"]["value"], "csv@example.com")
        self.assertIsNone(only_csv["phone"])

        # Only Res checks
        only_res = [
            p for p in profiles if p.get("name", {}).get("value") == "Only Res"
        ][0]
        self.assertEqual(only_res["email"]["value"], "res@example.com")

        # Check failed_candidates.json content
        with open(failed_json_path, "r", encoding="utf-8") as f:
            failures = json.load(f)

        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["stage"], "extraction")
        self.assertEqual(failures[0]["source"], "recruiter_csv")
        self.assertEqual(failures[0]["identifier"], "bad@example.com")


if __name__ == "__main__":
    unittest.main()
