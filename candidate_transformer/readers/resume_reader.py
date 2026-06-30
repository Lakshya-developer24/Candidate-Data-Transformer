"""
Module: candidate_transformer.readers.resume_reader

Responsible for reading raw text and structure from candidate resume files (PDF, Word, etc.).
Currently discovered files are restricted to UTF-8 encoded text files (.txt).
"""

from pathlib import Path
from typing import Dict, Union


class ResumeReader:
    """
    Reader for unstructured resume document files.
    """

    def read_resume_file(self, file_path: Union[str, Path]) -> str:
        """
        Reads a single resume file and returns its UTF-8 text content.

        Args:
            file_path: Path to the resume file.

        Returns:
            The raw text content of the resume.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the specified path is not a file or cannot be decoded as UTF-8.
            PermissionError: If access is denied by the filesystem.
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Resume file not found: {path}")

        if not path.is_file():
            raise ValueError(f"Specified path is not a file: {path}")

        try:
            with open(path, mode="r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError as e:
            raise ValueError(f"Failed to decode file {path.name} as UTF-8") from e
        except PermissionError as e:
            raise PermissionError(f"Permission denied reading file: {path.name}") from e

    def read_resumes(self, dir_path: Union[str, Path]) -> Dict[str, str]:
        """
        Discovers all .txt files in the given directory and reads their contents.

        Args:
            dir_path: Path to the directory containing candidate resumes.

        Returns:
            A dictionary mapping filenames (e.g. 'resume.txt') to their raw text content.

        Raises:
            FileNotFoundError: If the directory does not exist.
            NotADirectoryError: If the specified path is not a directory.
            PermissionError: If the system denies access to the directory or files.
            ValueError: If a file cannot be decoded as UTF-8.
        """
        path = Path(dir_path)

        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")

        if not path.is_dir():
            raise NotADirectoryError(f"Specified path is not a directory: {path}")

        resumes: Dict[str, str] = {}

        try:
            for file_path in path.iterdir():
                if file_path.is_file() and file_path.suffix == ".txt":
                    resumes[file_path.name] = self.read_resume_file(file_path)
        except PermissionError as e:
            raise PermissionError(f"Permission denied accessing directory: {path}") from e

        return resumes
