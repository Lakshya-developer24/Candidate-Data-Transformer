"""
Module: candidate_transformer.batch

Orchestrates batch-level candidate processing: scanning input directories,
triggering processing pipelines on multiple files, and saving results to output.
"""

import os
from typing import Any, Dict, List, Optional, Tuple
from candidate_transformer.pipeline import run_pipeline


def run_batch_processing(
    work_items: List[Dict[str, Any]], config: Optional[Dict[str, Any]] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Process all matched work items sequentially, catching exceptions per candidate
    to isolate failures.

    Args:
        work_items: A list of dicts, each with keys 'csv_row', 'resume_path',
                    'resume_text', 'row_index', 'source_filename'.
        config: Projection/validation configuration dictionary.

    Returns:
        A tuple of (profiles, failed_candidates).
    """
    if config is None:
        config = {}

    profiles = []
    failed_candidates = []

    for item in work_items:
        csv_row = item.get("csv_row")
        resume_path = item.get("resume_path")
        resume_text = item.get("resume_text")
        row_index = item.get("row_index")
        source_filename = item.get("source_filename")

        try:
            res = run_pipeline(
                csv_row=csv_row,
                resume_path=resume_path,
                resume_text=resume_text,
                config=config,
                row_index=row_index,
                source_filename=source_filename,
            )

            # A failure returned by run_pipeline has "stage" and "reason"
            if isinstance(res, dict) and "stage" in res and "reason" in res:
                failed_candidates.append(res)
            else:
                profiles.append(res)

        except Exception as e:
            # Exception safety fallback in case run_pipeline throws uncaught exception
            source_str = "unknown"
            if csv_row is not None and (
                resume_path is not None or resume_text is not None
            ):
                source_str = "both"
            elif csv_row is not None:
                source_str = "recruiter_csv"
            elif resume_path is not None or resume_text is not None:
                source_str = "resume_txt"

            identifier = "unidentified"
            if csv_row:
                identifier = (
                    csv_row.get("name")
                    or csv_row.get("email")
                    or "unidentified_csv_row"
                )
            elif resume_path:
                identifier = os.path.basename(resume_path)

            failed_candidates.append(
                {
                    "identifier": identifier,
                    "source": source_str,
                    "stage": "pipeline",
                    "reason": str(e),
                }
            )

    return profiles, failed_candidates
