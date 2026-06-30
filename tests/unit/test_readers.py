"""
Unit tests for the Reader layer of the candidate transformer.
Tests success and error scenarios for CSVReader and ResumeReader.
"""

import tempfile
import unittest
from pathlib import Path

from candidate_transformer.readers.csv_reader import CSVReader
from candidate_transformer.readers.resume_reader import ResumeReader


class TestCSVReader(unittest.TestCase):
    def setUp(self):
        self.reader = CSVReader()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_csv_reader_success(self):
        csv_file = self.temp_path / "valid.csv"
        csv_content = "name,email,phone\nJohn Doe,john@example.com,123456\nJane Smith,jane@example.com,654321\n"
        csv_file.write_text(csv_content, encoding="utf-8")

        result = self.reader.read_csv(csv_file)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "John Doe")
        self.assertEqual(result[0]["email"], "john@example.com")
        self.assertEqual(result[0]["phone"], "123456")
        self.assertEqual(result[1]["name"], "Jane Smith")

    def test_csv_reader_file_not_found(self):
        non_existent = self.temp_path / "missing.csv"
        with self.assertRaises(FileNotFoundError):
            self.reader.read_csv(non_existent)

    def test_csv_reader_not_a_file(self):
        with self.assertRaises(ValueError):
            self.reader.read_csv(self.temp_path)

    def test_csv_reader_empty(self):
        empty_file = self.temp_path / "empty.csv"
        empty_file.write_text("", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.reader.read_csv(empty_file)

    def test_csv_reader_whitespace_only(self):
        empty_file = self.temp_path / "empty_ws.csv"
        empty_file.write_text("   \n   \n", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.reader.read_csv(empty_file)


class TestResumeReader(unittest.TestCase):
    def setUp(self):
        self.reader = ResumeReader()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_resume_reader_success(self):
        # Create text files
        file1 = self.temp_path / "resume1.txt"
        file1.write_text("Resume of Alice", encoding="utf-8")

        file2 = self.temp_path / "resume2.txt"
        file2.write_text("Resume of Bob", encoding="utf-8")

        # Create a non-txt file (should be ignored)
        file3 = self.temp_path / "ignore.pdf"
        file3.write_text("Should be ignored", encoding="utf-8")

        result = self.reader.read_resumes(self.temp_path)
        self.assertEqual(len(result), 2)
        self.assertIn("resume1.txt", result)
        self.assertIn("resume2.txt", result)
        self.assertNotIn("ignore.pdf", result)
        self.assertEqual(result["resume1.txt"], "Resume of Alice")
        self.assertEqual(result["resume2.txt"], "Resume of Bob")

    def test_resume_reader_directory_not_found(self):
        non_existent = self.temp_path / "missing_dir"
        with self.assertRaises(FileNotFoundError):
            self.reader.read_resumes(non_existent)

    def test_resume_reader_not_a_directory(self):
        file_path = self.temp_path / "some_file.txt"
        file_path.write_text("content", encoding="utf-8")
        with self.assertRaises(NotADirectoryError):
            self.reader.read_resumes(file_path)

    def test_resume_reader_decode_error(self):
        bad_file = self.temp_path / "invalid_utf8.txt"
        # Write non-UTF-8 bytes
        bad_file.write_bytes(b"\x80\x81\x82")
        with self.assertRaises(ValueError):
            self.reader.read_resumes(self.temp_path)


if __name__ == "__main__":
    unittest.main()
