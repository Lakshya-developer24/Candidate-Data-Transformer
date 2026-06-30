"""
Module: candidate_transformer.validation

Validates candidate profiles and attributes against business rules, formatting standards,
and integrity constraints.
Validation only reports errors and never mutates input dictionaries.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from candidate_transformer.models import Candidate


@dataclass
class ValidationResult:
    """
    Structure representing the results of a validation check.
    """

    valid: bool
    errors: List[str] = field(default_factory=list)


def _find_missing_sentinels(val: Any) -> List[str]:
    """
    Recursively scans the projected output for missing-value sentinels.
    """
    errors = []
    if isinstance(val, dict):
        if val.get("__missing_error__") is True:
            field_path = val.get("field", "unknown")
            errors.append(f"required field '{field_path}' missing after projection")
        else:
            for v in val.values():
                errors.extend(_find_missing_sentinels(v))
    elif isinstance(val, list):
        for item in val:
            errors.extend(_find_missing_sentinels(item))
    return errors


def validate_field_type(val: Any, from_path: str, to_key: str) -> Optional[str]:
    """
    Checks that the type of the projected value matches the canonical schema type.
    """
    # Direct raw fields
    if from_path == "candidate_id":
        if not isinstance(val, str):
            return f"field '{to_key}' type mismatch: expected string, got {type(val).__name__}"
        return None
    if from_path == "overall_confidence":
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            return f"field '{to_key}' type mismatch: expected number, got {type(val).__name__}"
        return None

    # Determine expected inner type and if it expects an array
    if from_path in ("full_name", "headline", "location", "emails[0]", "phones[0]"):
        expected_inner = "string"
        is_array = False
    elif from_path == "years_experience":
        expected_inner = "number"
        is_array = False
    elif from_path in (
        "emails",
        "phones",
        "links",
        "skills",
        "skills[].value",
        "skills[].name",
    ):
        expected_inner = "string"
        is_array = True
    elif from_path in (
        "experience[].company",
        "experience[].title",
        "experience[].start",
        "experience[].end",
    ):
        expected_inner = "string"
        is_array = True
    elif from_path in (
        "education[].institution",
        "education[].degree",
        "education[].end",
    ):
        expected_inner = "string"
        is_array = True
    elif from_path == "experience":
        expected_inner = "experience_entry"
        is_array = True
    elif from_path == "education":
        expected_inner = "education_entry"
        is_array = True
    else:
        expected_inner = "string"
        is_array = False

    # Perform checks
    if is_array:
        if val is not None and not isinstance(val, list):
            return f"field '{to_key}' type mismatch: expected array, got {type(val).__name__}"
        if isinstance(val, list):
            for i, item in enumerate(val):
                if item is not None and not isinstance(item, dict):
                    return f"field '{to_key}[{i}]' type mismatch: expected object, got {type(item).__name__}"
                if isinstance(item, dict):
                    if expected_inner == "experience_entry":
                        for sub_f in ("company", "title", "start", "end"):
                            sub_val = item.get(sub_f)
                            if sub_val is not None:
                                err = validate_field_type(
                                    sub_val,
                                    sub_f,
                                    f"{to_key}[{i}].{sub_f}",
                                )
                                if err:
                                    return err
                    elif expected_inner == "education_entry":
                        for sub_f in ("institution", "degree", "end"):
                            sub_val = item.get(sub_f)
                            if sub_val is not None:
                                err = validate_field_type(
                                    sub_val,
                                    sub_f,
                                    f"{to_key}[{i}].{sub_f}",
                                )
                                if err:
                                    return err
                    else:
                        # CandidateValue dictionary
                        if "value" not in item:
                            return f"field '{to_key}[{i}]' missing 'value' property"
                        inner_val = item["value"]
                        if inner_val is not None:
                            if expected_inner == "string" and not isinstance(
                                inner_val, str
                            ):
                                return f"field '{to_key}[{i}].value' type mismatch: expected string, got {type(inner_val).__name__}"
                            if expected_inner == "number" and (
                                not isinstance(inner_val, (int, float))
                                or isinstance(inner_val, bool)
                            ):
                                return f"field '{to_key}[{i}].value' type mismatch: expected number, got {type(inner_val).__name__}"
    else:
        if val is not None and not isinstance(val, dict):
            return f"field '{to_key}' type mismatch: expected object, got {type(val).__name__}"
        if isinstance(val, dict):
            if "value" not in val:
                return f"field '{to_key}' missing 'value' property"
            inner_val = val["value"]
            if inner_val is not None:
                if expected_inner == "string" and not isinstance(inner_val, str):
                    return f"field '{to_key}.value' type mismatch: expected string, got {type(inner_val).__name__}"
                if expected_inner == "number" and (
                    not isinstance(inner_val, (int, float))
                    or isinstance(inner_val, bool)
                ):
                    return f"field '{to_key}.value' type mismatch: expected number, got {type(inner_val).__name__}"

    return None


def validate_projected(
    projected: Dict[str, Any], config: Dict[str, Any]
) -> ValidationResult:
    """
    Validates a projected candidate dictionary against output format constraints.
    Returns a ValidationResult containing errors. Never mutates the projected dictionary.
    """
    errors = []

    on_missing = config.get("on_missing", "null")

    # Read config fields mapping
    fields_config = config.get("fields")
    if fields_config is None:
        # Default all canonical fields
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

    # Required field sentinels check
    sentinel_errors = _find_missing_sentinels(projected)
    if on_missing == "error":
        errors.extend(sentinel_errors)

        # Check for completely absent fields in projected
        for f_cfg in fields_config:
            from_path = f_cfg.get("from")
            to_key = f_cfg.get("to", from_path)
            if to_key != "candidate_id" and to_key not in projected:
                errors.append(f"required field '{from_path}' missing after projection")

    # Type validation checks
    # Always check candidate_id if present
    if "candidate_id" in projected:
        type_err = validate_field_type(
            projected["candidate_id"], "candidate_id", "candidate_id"
        )
        if type_err:
            errors.append(type_err)

    for f_cfg in fields_config:
        from_path = f_cfg.get("from")
        to_key = f_cfg.get("to", from_path)

        if to_key in projected:
            if to_key == "candidate_id":
                continue
            val = projected[to_key]
            # Skip sentinel validation (already handled in sentinel checks)
            if isinstance(val, dict) and val.get("__missing_error__") is True:
                continue

            type_err = validate_field_type(val, from_path, to_key)
            if type_err:
                errors.append(type_err)

    return ValidationResult(valid=(len(errors) == 0), errors=errors)


def validate_candidate(candidate: Candidate) -> bool:
    """
    Validate the consolidated Candidate profile against default schema rules.
    """
    # Project with default configuration, then check validity
    from candidate_transformer.projection import project_candidate

    projected = project_candidate(candidate, {})
    result = validate_projected(projected, {})
    return result.valid
