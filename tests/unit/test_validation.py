"""
Unit tests for the Validation layer of the candidate transformer.
Tests success validation, missing value behaviors, type check failures, and robustness.
"""

import unittest
from candidate_transformer.validation import validate_projected


class TestValidation(unittest.TestCase):
    def test_valid_projected_happy_path(self):
        projected = {
            "candidate_id": "cand_1234",
            "full_name": {"value": "Jane Doe", "confidence": 1.0},
            "emails": [{"value": "jane.doe@example.com", "confidence": 1.0}],
            "phones": [],
            "overall_confidence": 0.85,
        }
        config = {
            "fields": [
                {"from": "full_name"},
                {"from": "emails"},
                {"from": "phones"},
                {"from": "overall_confidence"},
            ],
            "on_missing": "null",
        }

        res = validate_projected(projected, config)
        self.assertTrue(res.valid)
        self.assertEqual(len(res.errors), 0)

    def test_missing_required_field_error_mode(self):
        # field 'emails' is missing from projected, and on_missing is "error"
        projected = {
            "candidate_id": "cand_1234",
            "full_name": {"value": "Jane Doe", "confidence": 1.0},
        }
        config = {
            "fields": [{"from": "full_name"}, {"from": "emails"}],
            "on_missing": "error",
        }

        res = validate_projected(projected, config)
        self.assertFalse(res.valid)
        self.assertEqual(len(res.errors), 1)
        self.assertIn("required field 'emails' missing", res.errors[0])

    def test_missing_sentinel_detection(self):
        # field headline has sentinel dict in projected
        projected = {
            "candidate_id": "cand_1234",
            "headline": {"__missing_error__": True, "field": "headline"},
        }
        config = {
            "fields": [{"from": "headline"}],
            "on_missing": "error",
        }

        res = validate_projected(projected, config)
        self.assertFalse(res.valid)
        self.assertEqual(len(res.errors), 1)
        self.assertIn("required field 'headline' missing", res.errors[0])

    def test_missing_null_and_omit_modes_are_valid(self):
        # sentinel exists but mode is "null" -> valid
        projected_sentinel = {
            "candidate_id": "cand_1234",
            "headline": {"__missing_error__": True, "field": "headline"},
        }
        config_null = {
            "fields": [{"from": "headline"}],
            "on_missing": "null",
        }
        res_null = validate_projected(projected_sentinel, config_null)
        self.assertTrue(res_null.valid)

        # key is completely absent and mode is "omit" -> valid
        projected_absent = {
            "candidate_id": "cand_1234",
        }
        config_omit = {
            "fields": [{"from": "headline"}],
            "on_missing": "omit",
        }
        res_omit = validate_projected(projected_absent, config_omit)
        self.assertTrue(res_omit.valid)

    def test_type_validation_failures(self):
        # 1. overall_confidence must be number
        p1 = {
            "candidate_id": "cand_1234",
            "overall_confidence": "high",
        }
        config1 = {
            "fields": [{"from": "overall_confidence"}],
        }
        res1 = validate_projected(p1, config1)
        self.assertFalse(res1.valid)
        self.assertIn("expected number", res1.errors[0])

        # 2. full_name.value must be string
        p2 = {
            "candidate_id": "cand_1234",
            "full_name": {"value": 123, "confidence": 0.8},
        }
        config2 = {
            "fields": [{"from": "full_name"}],
        }
        res2 = validate_projected(p2, config2)
        self.assertFalse(res2.valid)
        self.assertIn("expected string", res2.errors[0])

        # 3. emails must be list (array)
        p3 = {
            "candidate_id": "cand_1234",
            "emails": {"value": "test@test.com"},
        }
        config3 = {
            "fields": [{"from": "emails"}],
        }
        res3 = validate_projected(p3, config3)
        self.assertFalse(res3.valid)
        self.assertIn("expected array", res3.errors[0])

    def test_multiple_validation_errors(self):
        projected = {
            "candidate_id": 123,  # type error: expected string
            "full_name": {"value": 100},  # type error: expected string
            "headline": {"__missing_error__": True, "field": "headline"},
        }
        config = {
            "fields": [
                {"from": "full_name"},
                {"from": "headline"},
            ],
            "on_missing": "error",
        }

        res = validate_projected(projected, config)
        self.assertFalse(res.valid)
        self.assertEqual(len(res.errors), 3)

    def test_projected_dict_not_mutated(self):
        projected = {
            "candidate_id": "cand_1234",
            "full_name": {"value": 123},
        }
        config = {
            "fields": [{"from": "full_name"}],
        }
        _ = validate_projected(projected, config)

        self.assertEqual(projected["full_name"]["value"], 123)


if __name__ == "__main__":
    unittest.main()
