"""
Module: candidate_transformer.id_generator

Generates stable, unique identifiers (IDs) for candidates based on key identifying fields
(such as normalized email or phone number hashes) to prevent duplication.
"""

import hashlib
from typing import Optional
from candidate_transformer.models import Candidate


def sha256(val: str) -> str:
    """
    Computes deterministic SHA-256 hash of a string value.
    """
    return hashlib.sha256(val.encode("utf-8")).hexdigest()


def generate_candidate_id(
    candidate: Candidate,
    source_filename: Optional[str] = None,
    row_index: Optional[int] = None,
) -> str:
    """
    Generate a unique, stable, and deterministic candidate ID based on key identifiers.
    Fallback order:
    1. Primary normalized email
    2. sha256(normalized_full_name + first_normalized_phone)[:12]
    3. sha256(source_filename + row_index)[:12]
    """
    # 1. Primary: normalized email
    if candidate.emails:
        email_cv = candidate.emails[0]
        if email_cv and email_cv.value is not None:
            email_clean = str(email_cv.value).strip().lower()
            if email_clean:
                return "cand_" + sha256(email_clean)[:12]

    # 2. Fallback 1: name + phone
    name_val = candidate.full_name.value if candidate.full_name else None
    phone_val = candidate.phones[0].value if candidate.phones else None

    if name_val is not None and phone_val is not None:
        name_clean = " ".join(str(name_val).lower().split())
        # Filter digits and '+'
        phone_clean = "".join(c for c in str(phone_val) if c.isdigit() or c == "+")
        if name_clean and phone_clean:
            return "cand_" + sha256(name_clean + phone_clean)[:12]

    # 3. Fallback 2: filename + index
    if source_filename is not None and row_index is not None:
        fn_clean = str(source_filename).strip()
        idx_clean = str(row_index).strip()
        return "cand_" + sha256(fn_clean + idx_clean)[:12]

    # Deterministic fallback of last resort (defaults to a fixed tag)
    fallback_seed = "last_resort_" + str(row_index if row_index is not None else 0)
    return "cand_" + sha256(fallback_seed)[:12]
