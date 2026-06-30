"""
Module: candidate_transformer.projection

Projects the internal Candidate model to target output formats and database schemas
according to configurations.
"""

import re
from typing import Any, Dict, List, Optional
from candidate_transformer.models import (
    Candidate,
    CandidateValue,
    EducationEntry,
    ExperienceEntry,
)

# Sentinels for missing-value handling
_OMIT_SENTINEL = object()
_ERROR_SENTINEL = object()


def resolve_path(candidate: Candidate, path: str) -> Any:
    """
    Resolves a canonical path string to extract raw values from a Candidate object.
    Supports only the specific paths documented in Data Schema.md.
    """
    if not candidate:
        return None

    # 1. Raw fields & overall_confidence
    if path in ("candidate_id", "overall_confidence"):
        return getattr(candidate, path, None)

    # 2. Scalar fields
    if path in ("full_name", "headline", "years_experience", "location"):
        return getattr(candidate, path, None)

    # 3. Whole list fields
    if path in ("emails", "phones", "skills", "links", "experience", "education"):
        return getattr(candidate, path, None)

    # 4. Indexed list fields (e.g., emails[0], phones[0])
    match_idx = re.match(r"^([a-z_]+)\[(\d+)\]$", path)
    if match_idx:
        field_name = match_idx.group(1)
        idx = int(match_idx.group(2))
        lst = getattr(candidate, field_name, None)
        if lst and idx < len(lst):
            return lst[idx]
        return None

    # 5. List sub-fields (e.g., skills[].value, skills[].name)
    if path in ("skills[].value", "skills[].name"):
        return candidate.skills

    # 6. Nested experience sub-fields (e.g., experience[].company)
    match_exp = re.match(r"^experience\[\]\.([a-z_]+)$", path)
    if match_exp:
        sub_field = match_exp.group(1)
        if not candidate.experience:
            return []
        res = []
        for entry in candidate.experience:
            if entry:
                res.append(getattr(entry, sub_field, None))
        return res

    # 7. Nested education sub-fields (e.g., education[].institution)
    match_edu = re.match(r"^education\[\]\.([a-z_]+)$", path)
    if match_edu:
        sub_field = match_edu.group(1)
        if not candidate.education:
            return []
        res = []
        for entry in candidate.education:
            if entry:
                res.append(getattr(entry, sub_field, None))
        return res

    return None


def project_field_val(
    resolved: Any, include_conf: bool, include_prov: bool, on_missing: str
) -> Any:
    """
    Recursively formats a resolved field value into the projected format.
    Respects metadata visibility toggles and missing-value configurations.
    """
    if resolved is None:
        if on_missing == "omit":
            return _OMIT_SENTINEL
        elif on_missing == "error":
            return _ERROR_SENTINEL
        else:  # "null"
            return None

    # CandidateValue Formatting
    if isinstance(resolved, CandidateValue):
        if resolved.value is None:
            if on_missing == "omit":
                return _OMIT_SENTINEL
            elif on_missing == "error":
                return _ERROR_SENTINEL
            else:  # "null"
                return None

        res = {"value": resolved.value}
        if include_conf:
            res["confidence"] = resolved.confidence
        if include_prov:
            res["source"] = resolved.source
            res["method"] = resolved.method
        return res

    # List Formatting
    if isinstance(resolved, list):
        if not resolved:
            return []

        # If list of CandidateValues
        if all(isinstance(x, CandidateValue) for x in resolved if x is not None):
            res_list = []
            for cv in resolved:
                p_val = project_field_val(cv, include_conf, include_prov, on_missing)
                if p_val is not _OMIT_SENTINEL:
                    res_list.append(p_val)
            return res_list

        # If list of ExperienceEntry
        if all(isinstance(x, ExperienceEntry) for x in resolved if x is not None):
            res_list = []
            for exp in resolved:
                if exp is None:
                    continue
                exp_dict = {}
                for field_name in ("company", "title", "start", "end"):
                    cv = getattr(exp, field_name, None)
                    p_val = project_field_val(cv, include_conf, include_prov, on_missing)
                    if p_val is not _OMIT_SENTINEL:
                        exp_dict[field_name] = p_val
                res_list.append(exp_dict)
            return res_list

        # If list of EducationEntry
        if all(isinstance(x, EducationEntry) for x in resolved if x is not None):
            res_list = []
            for edu in resolved:
                if edu is None:
                    continue
                edu_dict = {}
                for field_name in ("institution", "degree", "end"):
                    cv = getattr(edu, field_name, None)
                    p_val = project_field_val(cv, include_conf, include_prov, on_missing)
                    if p_val is not _OMIT_SENTINEL:
                        edu_dict[field_name] = p_val
                res_list.append(edu_dict)
            return res_list

        # Mixed lists (e.g. list of None and CandidateValue)
        res_list = []
        for item in resolved:
            p_val = project_field_val(item, include_conf, include_prov, on_missing)
            if p_val is not _OMIT_SENTINEL:
                res_list.append(p_val)
        return res_list

    # Raw types (candidate_id / overall_confidence)
    return resolved


def project_candidate(
    candidate: Candidate, config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Transforms the internal Candidate model representation to the target external schema.
    Produces an output dictionary using the provided configuration, leaving the Candidate unchanged.
    """
    if config is None:
        config = {}

    include_conf = config.get("include_confidence", True)
    include_prov = config.get("include_provenance", True)
    on_missing = config.get("on_missing", "null")

    fields_config = config.get("fields")
    if fields_config is None:
        # Default projection includes all canonical fields
        fields_config = [
            {"from": "full_name", "to": "full_name"},
            {"from": "emails", "to": "emails"},
            {"from": "phones", "to": "phones"},
            {"from": "location", "to": "location"},
            {"from": "links", "to": "links"},
            {"from": "headline", "to": "headline"},
            {"from": "years_experience", "to": "years_experience"},
            {"from": "skills", "to": "skills"},
            {"from": "experience", "to": "experience"},
            {"from": "education", "to": "education"},
            {"from": "overall_confidence", "to": "overall_confidence"},
        ]

    projected = {}

    # candidate_id is ALWAYS included as raw string, directly, not formatted as CandidateValue
    projected["candidate_id"] = candidate.candidate_id if candidate else ""

    for f_cfg in fields_config:
        from_path = f_cfg.get("from")
        to_key = f_cfg.get("to", from_path)

        if to_key == "candidate_id":
            continue

        resolved = resolve_path(candidate, from_path)
        p_val = project_field_val(resolved, include_conf, include_prov, on_missing)

        if p_val is _OMIT_SENTINEL:
            continue
        elif p_val is _ERROR_SENTINEL:
            projected[to_key] = {"__missing_error__": True, "field": from_path}
        else:
            projected[to_key] = p_val

    return projected
