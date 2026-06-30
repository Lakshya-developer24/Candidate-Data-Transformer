"""
Module: candidate_transformer.matcher

Responsible for matching candidate records across different data sources.
Uses identifiers like email, phone numbers, and names to compute match probability.
"""

from typing import Any, Dict, List, Tuple
from candidate_transformer.extractors.resume_extractor import ResumeExtractor
from candidate_transformer.normalization import normalize_candidate


class CandidateMatcher:
    """
    Matches candidate records across CSV rows and resumes using normalized primary email.
    """

    def match(
        self,
        csv_rows: List[Dict[str, Any]],
        resumes: Dict[str, Tuple[str, str]],  # maps filename -> (path, text)
    ) -> List[Dict[str, Any]]:
        """
        Deduplicates and groups recruiter CSV rows and resumes.
        """
        work_items = []

        # 1. Extract and normalize email from resumes
        extracted_resumes = []
        for filename, (path, text) in resumes.items():
            email = None
            try:
                extractor = ResumeExtractor()
                cand = extractor.extract_from_text(text)
                normalize_candidate(cand)
                if cand.emails:
                    email = cand.emails[0].value
            except Exception:
                pass
            extracted_resumes.append(
                {"filename": filename, "path": path, "text": text, "email": email}
            )

        # 2. Match loop
        matched_csv_indices = set()
        matched_resume_filenames = set()

        for csv_idx, row in enumerate(csv_rows):
            csv_email = row.get("email")
            if csv_email:
                csv_email_clean = str(csv_email).strip().lower()
            else:
                csv_email_clean = None

            match_found = False
            if csv_email_clean:
                for res_info in extracted_resumes:
                    res_email = res_info["email"]
                    if res_email and res_email.strip().lower() == csv_email_clean:
                        work_items.append(
                            {
                                "csv_row": row,
                                "resume_path": res_info["path"],
                                "resume_text": res_info["text"],
                            }
                        )
                        matched_csv_indices.add(csv_idx)
                        matched_resume_filenames.add(res_info["filename"])
                        match_found = True
                        break

        # 3. Add unmatched CSV rows
        for csv_idx, row in enumerate(csv_rows):
            if csv_idx not in matched_csv_indices:
                work_items.append({"csv_row": row})

        # 4. Add unmatched Resumes
        for res_info in extracted_resumes:
            if res_info["filename"] not in matched_resume_filenames:
                work_items.append(
                    {"resume_path": res_info["path"], "resume_text": res_info["text"]}
                )

        return work_items


def check_match(candidate_a: Any, candidate_b: Any) -> float:
    """
    Calculate a similarity score between two candidates.
    Matches exactly if normalized emails match.
    """
    # Simple compatibility layer matching the skeleton signature
    if candidate_a and candidate_b:
        email_a = (
            candidate_a.emails[0].value if candidate_a.emails else ""
        )
        email_b = (
            candidate_b.emails[0].value if candidate_b.emails else ""
        )
        if email_a and email_b and email_a.strip().lower() == email_b.strip().lower():
            return 1.0
    return 0.0
