"""
Module: candidate_transformer.normalization

Responsible for normalizing candidate fields (emails, phone numbers, dates, skills)
to a standard format for accurate matching and merging.
Normalization operates in place on CandidateValue.value.
"""

import re
from typing import Any, Dict
from candidate_transformer.models import Candidate, CandidateValue

# Skill alias dictionary for case-insensitive lookup.
SKILL_ALIASES: Dict[str, str] = {
    "js": "JavaScript",
    "k8s": "Kubernetes",
    "postgres": "PostgreSQL",
}


def normalize_email(email_val: CandidateValue) -> CandidateValue:
    """
    Normalize an email address (lowercase, trim whitespace) in place.

    Args:
        email_val: The CandidateValue holding the email string.

    Returns:
        The mutated CandidateValue object.
    """
    if email_val and email_val.value is not None:
        email_val.value = str(email_val.value).strip().lower()
    return email_val


def normalize_phone(phone_val: CandidateValue) -> CandidateValue:
    """
    Normalize a phone number to standard international E.164 format in place.

    Args:
        phone_val: The CandidateValue holding the phone string.

    Returns:
        The mutated CandidateValue object.
    """
    if phone_val and phone_val.value is not None:
        val_str = str(phone_val.value).strip()
        if not val_str:
            phone_val.value = ""
            return phone_val

        # Filter only digits and '+'
        cleaned = "".join(c for c in val_str if c.isdigit() or c == "+")
        if cleaned.startswith("+"):
            digits = "".join(c for c in cleaned[1:] if c.isdigit())
            phone_val.value = "+" + digits
        else:
            digits = "".join(c for c in cleaned if c.isdigit())
            if len(digits) == 10:
                phone_val.value = "+1" + digits
            elif len(digits) == 11 and digits.startswith("1"):
                phone_val.value = "+" + digits
            else:
                if digits:
                    phone_val.value = "+" + digits
                else:
                    phone_val.value = ""
    return phone_val


def normalize_date_str(val: Any) -> Any:
    """
    Normalize a date string (Mon YYYY, YYYY, or Present) to YYYY-MM or None.

    Args:
        val: The raw value to normalize.

    Returns:
        The normalized string or None.
    """
    if val is None:
        return None
    val_str = str(val).strip()
    if not val_str:
        return ""
    if val_str.lower() == "present":
        return None

    # Check if already in YYYY-MM format
    if re.match(r"^\d{4}-\d{2}$", val_str):
        return val_str

    months = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
        "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"
    }

    # Match Mon YYYY (case-insensitive)
    match_mon_year = re.match(r"^([A-Za-z]{3})\s+(\d{4})$", val_str)
    if match_mon_year:
        mon = match_mon_year.group(1).lower()
        year = match_mon_year.group(2)
        if mon in months:
            return f"{year}-{months[mon]}"

    # Match 4-digit YYYY
    match_year = re.match(r"^(\d{4})$", val_str)
    if match_year:
        year = match_year.group(1)
        return f"{year}-01"

    # If unrecognized, pass through unmodified
    return val_str


def normalize_candidate(candidate: Candidate) -> None:
    """
    Normalizes all field values of the Candidate object in-place.
    Only modifies CandidateValue.value. Never alters metadata.

    Args:
        candidate: The Candidate object to mutate.
    """
    if not candidate:
        return

    # Normalize full_name (no rules defined, but strip if present to be clean)
    if candidate.full_name and candidate.full_name.value is not None:
        candidate.full_name.value = str(candidate.full_name.value).strip()

    # Normalize emails
    if candidate.emails:
        for email_cv in candidate.emails:
            if email_cv:
                normalize_email(email_cv)

    # Normalize phones
    if candidate.phones:
        for phone_cv in candidate.phones:
            if phone_cv:
                normalize_phone(phone_cv)

    # Normalize location & headline (strip if present)
    if candidate.location and candidate.location.value is not None:
        candidate.location.value = str(candidate.location.value).strip()
    if candidate.headline and candidate.headline.value is not None:
        candidate.headline.value = str(candidate.headline.value).strip()

    # Normalize skills
    if candidate.skills:
        for skill_cv in candidate.skills:
            if skill_cv and skill_cv.value is not None:
                skill_str = str(skill_cv.value).strip()
                skill_lower = skill_str.lower()
                if skill_lower in SKILL_ALIASES:
                    skill_cv.value = SKILL_ALIASES[skill_lower]
                else:
                    skill_cv.value = skill_str

    # Normalize experience dates
    if candidate.experience:
        for exp in candidate.experience:
            if exp:
                # company and title strip
                if exp.company and exp.company.value is not None:
                    exp.company.value = str(exp.company.value).strip()
                if exp.title and exp.title.value is not None:
                    exp.title.value = str(exp.title.value).strip()
                if exp.start:
                    exp.start.value = normalize_date_str(exp.start.value)
                if exp.end:
                    exp.end.value = normalize_date_str(exp.end.value)

    # Normalize education dates
    if candidate.education:
        for edu in candidate.education:
            if edu:
                # institution and degree strip
                if edu.institution and edu.institution.value is not None:
                    edu.institution.value = str(edu.institution.value).strip()
                if edu.degree and edu.degree.value is not None:
                    edu.degree.value = str(edu.degree.value).strip()
                if edu.end:
                    edu.end.value = normalize_date_str(edu.end.value)
