"""
Module: candidate_transformer.readers.csv_reader

Responsible for reading raw CSV candidate tabular files.
Provides safe file access and maps contents into dictionaries, preserving the schema.
"""

import csv
from pathlib import Path
from typing import Any, Dict, List, Union


class CSVReader:
    """
    Reader for tabular CSV candidates data source.
    """

    def read_csv(self, file_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """
        Reads a CSV file and returns a list of dictionaries representing each row.

        Args:
            file_path: Path to the CSV file.

        Returns:
            A list of dictionaries representing rows, mapping column headers to cell values.

        Raises:
            FileNotFoundError: If the file does not exist or is not a file.
            PermissionError: If the system denies read access to the file.
            ValueError: If the file is empty, has an invalid format, or fails to parse.
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {path}")

        if not path.is_file():
            raise ValueError(f"Specified path is not a file: {path}")

        try:
            with open(path, mode="r", encoding="utf-8", newline="") as f:
                # Read contents into a DictReader.
                # We can perform a quick check to see if the file is empty.
                content = f.read(1024)
                if not content.strip():
                    raise ValueError(f"CSV file is empty: {path}")
                f.seek(0)

                reader = csv.DictReader(f)
                if reader.fieldnames is None or not reader.fieldnames:
                    raise ValueError(f"CSV file has no headers or invalid format: {path}")

                rows: List[Dict[str, Any]] = []
                for row in reader:
                    # Clean up rows to ensure they are standard dicts (not OrderedDicts)
                    rows.append(dict(row))
                return rows

        except PermissionError as e:
            raise PermissionError(f"Permission denied accessing file: {path}") from e
        except csv.Error as e:
            raise ValueError(f"Malformed or invalid CSV format in file: {path}") from e
        except UnicodeDecodeError as e:
            raise ValueError(f"Failed to decode CSV file as UTF-8: {path}") from e
