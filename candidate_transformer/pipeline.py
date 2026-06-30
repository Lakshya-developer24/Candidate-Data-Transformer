"""
Module: candidate_transformer.pipeline

Orchestrates the complete candidate processing pipeline from source data
reading, extraction, normalization, matching, merging, validation, and projection.
"""

import os
from typing import Any, Dict, Optional
from candidate_transformer.extractors.csv_extractor import CSVExtractor
from candidate_transformer.extractors.resume_extractor import ResumeExtractor
from candidate_transformer.normalization import normalize_candidate
from candidate_transformer.merge import merge_candidates
from candidate_transformer.projection import project_candidate
from candidate_transformer.validation import validate_projected
from candidate_transformer.id_generator import generate_candidate_id
from candidate_transformer.readers.resume_reader import ResumeReader


def run_pipeline(
    csv_row: Optional[Dict[str, Any]] = None,
    resume_path: Optional[str] = None,
    resume_text: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    row_index: Optional[int] = None,
    source_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute the pipeline steps sequentially for a single candidate profile data source.
    Returns the projected dictionary on success, or a structured failure dictionary on failure.
    """
    if config is None:
        config = {}

    # Determine source string for failures
    if csv_row is not None and (resume_path is not None or resume_text is not None):
        source_str = "both"
    elif csv_row is not None:
        source_str = "recruiter_csv"
    elif resume_path is not None or resume_text is not None:
        source_str = "resume_txt"
    else:
        source_str = "unknown"

    # Determine identifier for failures
    identifier = "unidentified"
    if csv_row:
        identifier = (
            csv_row.get("name") or csv_row.get("email") or "unidentified_csv_row"
        )
    elif resume_path:
        identifier = os.path.basename(resume_path)
    elif resume_text:
        lines = [l.strip() for l in resume_text.splitlines() if l.strip()]
        if lines:
            identifier = lines[0]

    try:
        # 1. Reader
        if resume_path is not None and resume_text is None:
            try:
                reader = ResumeReader()
                resume_text = reader.read_resume_file(resume_path)
            except Exception as e:
                return {
                    "identifier": identifier,
                    "source": source_str,
                    "stage": "reader",
                    "reason": str(e),
                }

        # 2. Extractor
        candidate_csv = None
        if csv_row is not None:
            try:
                extractor = CSVExtractor()
                candidate_csv = extractor.extract(csv_row)
            except Exception as e:
                return {
                    "identifier": identifier,
                    "source": source_str,
                    "stage": "extraction",
                    "reason": str(e),
                }

        candidate_resume = None
        if resume_text is not None:
            try:
                extractor = ResumeExtractor()
                candidate_resume = extractor.extract_from_text(resume_text)
            except Exception as e:
                return {
                    "identifier": identifier,
                    "source": source_str,
                    "stage": "extraction",
                    "reason": str(e),
                }

        # 3. Normalization
        if candidate_csv is not None:
            try:
                normalize_candidate(candidate_csv)
            except Exception as e:
                return {
                    "identifier": identifier,
                    "source": source_str,
                    "stage": "normalization",
                    "reason": str(e),
                }

        if candidate_resume is not None:
            try:
                normalize_candidate(candidate_resume)
            except Exception as e:
                return {
                    "identifier": identifier,
                    "source": source_str,
                    "stage": "normalization",
                    "reason": str(e),
                }

        # 4. Merge
        candidate = None
        if candidate_csv is not None and candidate_resume is not None:
            try:
                candidate = merge_candidates(candidate_csv, candidate_resume)
            except Exception as e:
                return {
                    "identifier": identifier,
                    "source": source_str,
                    "stage": "merge",
                    "reason": str(e),
                }
        elif candidate_csv is not None:
            candidate = candidate_csv
        elif candidate_resume is not None:
            candidate = candidate_resume
        else:
            return {
                "identifier": identifier,
                "source": source_str,
                "stage": "pipeline",
                "reason": "No data provided to pipeline",
            }

        # Generate Candidate ID
        if candidate:
            candidate.candidate_id = generate_candidate_id(
                candidate,
                source_filename=source_filename,
                row_index=row_index,
            )

        # 5. Projection
        try:
            projected = project_candidate(candidate, config)
        except Exception as e:
            return {
                "identifier": identifier,
                "source": source_str,
                "stage": "projection",
                "reason": str(e),
            }

        # 6. Validation
        try:
            val_res = validate_projected(projected, config)
            if not val_res.valid:
                reason_str = "; ".join(val_res.errors)
                return {
                    "identifier": identifier,
                    "source": source_str,
                    "stage": "validation",
                    "reason": reason_str,
                }
        except Exception as e:
            return {
                "identifier": identifier,
                "source": source_str,
                "stage": "validation",
                "reason": str(e),
            }

        # Success: Return projected output dictionary
        return projected

    except Exception as e:
        return {
            "identifier": identifier,
            "source": source_str,
            "stage": "pipeline",
            "reason": str(e),
        }
