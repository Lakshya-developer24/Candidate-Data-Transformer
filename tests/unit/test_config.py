"""
Unit tests for the Config Loader of the candidate transformer.
Tests loading valid and invalid configuration schema shapes.
"""

import json
import os
import tempfile
import unittest
from candidate_transformer.config import Config


class TestConfig(unittest.TestCase):
    def test_default_config(self):
        cfg = Config()
        self.assertTrue(cfg.get("include_confidence"))
        self.assertTrue(cfg.get("include_provenance"))
        self.assertEqual(cfg.get("on_missing"), "null")
        self.assertIsNone(cfg.get("fields"))

    def test_load_valid_config(self):
        config_data = {
            "include_confidence": False,
            "on_missing": "omit",
            "fields": [
                {"from": "full_name", "to": "name"},
                {"from": "emails[0]"}
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            json.dump(config_data, f)
            temp_name = f.name

        try:
            cfg = Config(temp_name)
            self.assertFalse(cfg.get("include_confidence"))
            self.assertEqual(cfg.get("on_missing"), "omit")
            fields = cfg.get("fields")
            self.assertEqual(len(fields), 2)
            self.assertEqual(fields[0]["from"], "full_name")
            self.assertEqual(fields[0]["to"], "name")
            self.assertEqual(fields[1]["from"], "emails[0]")
        finally:
            os.remove(temp_name)

    def test_load_invalid_config_shape(self):
        # 1. Invalid on_missing
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            json.dump({"on_missing": "raise"}, f)
            temp_name = f.name
        try:
            with self.assertRaises(ValueError):
                Config(temp_name)
        finally:
            os.remove(temp_name)

        # 2. Invalid fields type
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            json.dump({"fields": "not-a-list"}, f)
            temp_name = f.name
        try:
            with self.assertRaises(ValueError):
                Config(temp_name)
        finally:
            os.remove(temp_name)


if __name__ == "__main__":
    unittest.main()
