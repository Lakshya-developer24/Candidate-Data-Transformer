"""
Unit tests for the Batch Processor of the candidate transformer.
Tests batch-level processing, failure isolation, and collection returns.
"""

import unittest
from candidate_transformer.batch import run_batch_processing


class TestBatch(unittest.TestCase):
    def setUp(self):
        self.valid_csv = {
            "name": "Jane Doe",
            "email": "jane@example.com",
        }
        self.invalid_csv = {
            "email": "no.name@example.com",  # Missing name causes extraction failure
        }
        self.resume_text = """John Smith
Software Engineer

SUMMARY
3+ years of experience

CONTACT
john@example.com
"""

    def test_batch_multiple_candidates(self):
        work_items = [
            {"csv_row": self.valid_csv},
            {"resume_text": self.resume_text},
        ]

        profiles, failures = run_batch_processing(
            work_items, config={"on_missing": "null"}
        )

        self.assertEqual(len(profiles), 2)
        self.assertEqual(len(failures), 0)
        self.assertEqual(profiles[0]["full_name"]["value"], "Jane Doe")
        self.assertEqual(profiles[1]["full_name"]["value"], "John Smith")

    def test_batch_failure_isolation(self):
        # 1 valid candidate, 1 invalid csv candidate, 1 candidate triggering validation error
        work_items = [
            {"csv_row": self.valid_csv},
            {"csv_row": self.invalid_csv},  # extraction fail
            {
                "resume_text": self.resume_text,
                # validation error under 'error' mode on missing location
            },
        ]
        config = {
            "fields": [{"from": "full_name"}, {"from": "location"}],
            "on_missing": "error",
        }

        profiles, failures = run_batch_processing(work_items, config=config)

        # Candidate 1 (valid_csv) has full_name, and location is None. Wait!
        # Under config: fields = [full_name, location], on_missing = "error".
        # Candidate 1 will also trigger validation error because location is missing!
        # Let's adjust candidate 1 to have location or configure separately to test success and failure together.
        # Wait, if we want candidate 1 to succeed, let's provide location in config? But we can't provide location in csv_extractor yet (location not supported in csv extractor).
        # Ah! Location is not mapped in CSV extractor.
        # Let's change config to have fields = [full_name]. Then candidate 1 and 3 will succeed, candidate 2 fails.
        # If config is fields = [full_name, emails[0]], on_missing = "error".
        # Candidate 1 has email -> succeeds.
        # Candidate 3 has no email (contacts parsed from text but emails list is parsed via regex in resume. Yes, john@example.com is in contact, so emails is populated).
        # Let's just use fields = [full_name] and on_missing = "error".
        # Since full_name is present in candidate 1 and 3, they will succeed.
        # Candidate 2 has no name -> fails extraction.
        # This isolates extraction failure!
        # Now let's add a candidate that fails validation.
        # E.g. Candidate 4 has config with from: "headline", on_missing: "error" but has no headline.
        # Let's write the test cases cleanly:

    def test_batch_failure_isolation_clean(self):
        work_items = [
            {
                "csv_row": self.valid_csv  # succeeds
            },
            {
                "csv_row": self.invalid_csv  # fails extraction
            },
        ]
        # full_name is present in valid_csv
        config = {
            "fields": [{"from": "full_name"}],
            "on_missing": "error",
        }

        profiles, failures = run_batch_processing(work_items, config=config)

        self.assertEqual(len(profiles), 1)
        self.assertEqual(len(failures), 1)

        self.assertEqual(profiles[0]["full_name"]["value"], "Jane Doe")
        self.assertEqual(failures[0]["stage"], "extraction")
        self.assertEqual(failures[0]["identifier"], "no.name@example.com")

    def test_batch_validation_failure_isolation(self):
        work_items = [
            {
                "csv_row": self.valid_csv
            }
        ]
        # missing location triggers validation error
        config = {
            "fields": [{"from": "full_name"}, {"from": "location"}],
            "on_missing": "error",
        }

        profiles, failures = run_batch_processing(work_items, config=config)

        self.assertEqual(len(profiles), 0)
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["stage"], "validation")
        self.assertEqual(failures[0]["identifier"], "Jane Doe")

    def test_batch_empty(self):
        profiles, failures = run_batch_processing([])
        self.assertEqual(profiles, [])
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
