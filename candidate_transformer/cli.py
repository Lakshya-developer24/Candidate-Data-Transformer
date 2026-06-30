"""
Module: candidate_transformer.cli

Responsible for the Command Line Interface (CLI) of the candidate transformer tool.
It allows users to run pipelines or batch processing from the terminal with custom configurations.
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List

from candidate_transformer.batch import run_batch_processing
from candidate_transformer.config import Config
from candidate_transformer.matcher import CandidateMatcher
from candidate_transformer.readers.csv_reader import CSVReader
from candidate_transformer.readers.resume_reader import ResumeReader


def main() -> None:
    """
    Parse command-line arguments and run the configured candidate processing task.
    """
    parser = argparse.ArgumentParser(
        description="Multi Source Candidate Data Transformer"
    )
    parser.add_argument("--csv", required=True, help="Path to recruiter CSV file")
    parser.add_argument("--resumes", required=True, help="Path to resumes directory")
    parser.add_argument("--config", help="Path to config JSON file")
    parser.add_argument("--out", default="output", help="Path to output directory")

    args = parser.parse_args()

    try:
        # 1. Load config
        if args.config:
            config_obj = Config(args.config)
        else:
            config_obj = Config()
        config = config_obj.config_data

        # 2. Read recruiter CSV
        csv_reader = CSVReader()
        rows = csv_reader.read_csv(args.csv)

        # 3. Read resumes
        resume_reader = ResumeReader()
        resumes_raw = resume_reader.read_resumes(args.resumes)

        resumes_for_matcher = {}
        for name, text in resumes_raw.items():
            path = os.path.join(args.resumes, name)
            resumes_for_matcher[name] = (path, text)

        # 4. Match candidates
        matcher = CandidateMatcher()
        work_items = matcher.match(rows, resumes_for_matcher)

        # Add source_filename and row_index to work items
        csv_filename = os.path.basename(args.csv)
        csv_row_to_index = {id(row): idx for idx, row in enumerate(rows)}

        for item in work_items:
            csv_row = item.get("csv_row")
            if csv_row is not None:
                item["row_index"] = csv_row_to_index.get(id(csv_row))
                item["source_filename"] = csv_filename

        # 5. Run batch processing
        profiles, failed_candidates = run_batch_processing(work_items, config)

        # 6. Write output files
        out_dir = args.out
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        profiles_path = os.path.join(out_dir, "profiles.json")
        failed_path = os.path.join(out_dir, "failed_candidates.json")

        with open(profiles_path, "w", encoding="utf-8") as f:
            json.dump(profiles, f, indent=2)

        with open(failed_path, "w", encoding="utf-8") as f:
            json.dump(failed_candidates, f, indent=2)

        # 7. Print exactly one summary line
        total = len(profiles) + len(failed_candidates)
        success = len(profiles)
        failed = len(failed_candidates)
        print(
            f"Processed {total} candidates: {success} succeeded, {failed} failed. "
            f"See {out_dir}/profiles.json and {out_dir}/failed_candidates.json."
        )

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
