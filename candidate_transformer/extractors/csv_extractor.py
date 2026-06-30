"""
Module: candidate_transformer.extractors.csv_extractor

Extracts and parses fields from CSV row dictionaries to map them into Candidate data models.
Maps name, email, phone, and constructs a single ExperienceEntry if company/title are present.
"""

from typing import Any, Dict
from candidate_transformer.models import Candidate, CandidateValue, ExperienceEntry


class CSVExtractor:
    """
    Extractor for mapping structured CSV rows into candidate profiles.
    """

    def extract(self, raw_data: Dict[str, Any]) -> Candidate:
        """
        Parse single CSV row record and instantiate a Candidate model.

        Args:
            raw_data: A dictionary containing raw column mappings for a CSV row.

        Returns:
            A populated Candidate model instance.

        Raises:
            ValueError: If the required 'name' field is missing or empty.
        """
        # Read and check name. Column names are case-sensitive matching the schema.
        name_val = raw_data.get("name")
        if name_val is None or not str(name_val).strip():
            raise ValueError("CSV row is missing required field 'name'")

        name_str = str(name_val).strip()

        # CSV direct extraction parameters
        source_name = "recruiter_csv"
        method_name = "csv_direct"
        confidence_score = 0.95

        # Create full_name CandidateValue
        full_name = CandidateValue(
            value=name_str,
            confidence=confidence_score,
            source=source_name,
            method=method_name,
        )

        # Emails list - only populate if email is present and non-empty
        emails = []
        email_val = raw_data.get("email")
        if email_val is not None and str(email_val).strip():
            emails.append(
                CandidateValue(
                    value=str(email_val).strip(),
                    confidence=confidence_score,
                    source=source_name,
                    method=method_name,
                )
            )

        # Phones list - only populate if phone is present and non-empty
        phones = []
        phone_val = raw_data.get("phone")
        if phone_val is not None and str(phone_val).strip():
            phones.append(
                CandidateValue(
                    value=str(phone_val).strip(),
                    confidence=confidence_score,
                    source=source_name,
                    method=method_name,
                )
            )

        # Experience entry - combine company and title
        experience = []
        company = raw_data.get("company")
        title = raw_data.get("title")

        has_company = company is not None and str(company).strip()
        has_title = title is not None and str(title).strip()

        if has_company or has_title:
            comp_cv = (
                CandidateValue(
                    value=str(company).strip(),
                    confidence=confidence_score,
                    source=source_name,
                    method=method_name,
                )
                if has_company
                else None
            )
            title_cv = (
                CandidateValue(
                    value=str(title).strip(),
                    confidence=confidence_score,
                    source=source_name,
                    method=method_name,
                )
                if has_title
                else None
            )

            experience.append(
                ExperienceEntry(
                    company=comp_cv,
                    title=title_cv,
                    start=None,
                    end=None,
                )
            )

        # Return Candidate object. Other fields remain None/empty as per specifications.
        return Candidate(
            candidate_id="",
            full_name=full_name,
            emails=emails,
            phones=phones,
            location=None,
            links=[],
            headline=None,
            years_experience=None,
            skills=[],
            experience=experience,
            education=[],
            overall_confidence=0.0,
        )
