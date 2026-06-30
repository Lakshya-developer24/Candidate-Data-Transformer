"""
Module: candidate_transformer.merge

Implements merging logic to consolidate two matched candidate objects into a single profile.
Handles conflict resolution, duplicates, and calculates overall confidence scores.
"""

from typing import Any, List, Optional, Union
from candidate_transformer.models import (
    Candidate,
    CandidateValue,
    EducationEntry,
    ExperienceEntry,
)


def merge_scalar_values(
    val_a: Optional[CandidateValue], val_b: Optional[CandidateValue]
) -> Optional[CandidateValue]:
    """
    Deterministically merges two scalar CandidateValue objects.

    Args:
        val_a: First CandidateValue to merge (can be None).
        val_b: Second CandidateValue to merge (can be None).

    Returns:
        A new CandidateValue representing the merged result, or None.
    """
    # Rule 1: If one value is None, return a copy of the other value.
    a_is_none = val_a is None or val_a.value is None
    b_is_none = val_b is None or val_b.value is None

    if a_is_none:
        if val_b is None or val_b.value is None:
            return None
        return CandidateValue(
            value=val_b.value,
            confidence=val_b.confidence,
            source=val_b.source,
            method=val_b.method,
        )

    if b_is_none:
        return CandidateValue(
            value=val_a.value,
            confidence=val_a.confidence,
            source=val_a.source,
            method=val_a.method,
        )

    # Rule 2: If both values exist and are equal (already normalized), return agreed.
    if val_a.value == val_b.value:
        higher_conf = max(val_a.confidence, val_b.confidence)
        confidence = round(min(1.0, higher_conf + 0.05), 4)

        # Combine sources into a sorted, unique list or string
        sources = set()
        for src in (val_a.source, val_b.source):
            if isinstance(src, list):
                sources.update(src)
            elif src:
                sources.add(src)

        combined_sources = sorted(list(sources))
        if len(combined_sources) == 1:
            source_res = combined_sources[0]
        else:
            source_res = combined_sources

        return CandidateValue(
            value=val_a.value,
            confidence=confidence,
            source=source_res,
            method="agreed",
        )

    # Rule 3: If values differ, higher confidence wins.
    if val_a.confidence > val_b.confidence:
        return CandidateValue(
            value=val_a.value,
            confidence=val_a.confidence,
            source=val_a.source,
            method=val_a.method,
        )

    if val_b.confidence > val_a.confidence:
        return CandidateValue(
            value=val_b.value,
            confidence=val_b.confidence,
            source=val_b.source,
            method=val_b.method,
        )

    # Rule 4: If confidence is exactly equal, prefer method == "csv_direct"
    if val_a.method == "csv_direct" and val_b.method != "csv_direct":
        return CandidateValue(
            value=val_a.value,
            confidence=val_a.confidence,
            source=val_a.source,
            method=val_a.method,
        )

    if val_b.method == "csv_direct" and val_a.method != "csv_direct":
        return CandidateValue(
            value=val_b.value,
            confidence=val_b.confidence,
            source=val_b.source,
            method=val_b.method,
        )

    # Default fallback tie-breaker (prefer left value val_a)
    return CandidateValue(
        value=val_a.value,
        confidence=val_a.confidence,
        source=val_a.source,
        method=val_a.method,
    )


def _normalize_str_for_key(val: Optional[Any]) -> str:
    """
    Normalizes a string for deduplication key comparison.
    Converts to lowercase, strips outer whitespace, and collapses internal spaces.
    """
    if val is None:
        return ""
    return " ".join(str(val).lower().split())


def _merge_candidate_value_list(
    list_a: List[CandidateValue], list_b: List[CandidateValue]
) -> List[CandidateValue]:
    """
    Deduplicates and merges two lists of CandidateValue objects deterministically.
    Duplicates are resolved using merge_scalar_values.
    """
    merged_dict = {}
    order = []

    lst_a = list_a if list_a else []
    lst_b = list_b if list_b else []

    for cv in lst_a + lst_b:
        if cv is None or cv.value is None:
            continue
        val_str = str(cv.value)
        if val_str not in merged_dict:
            merged_dict[val_str] = CandidateValue(
                value=cv.value,
                confidence=cv.confidence,
                source=cv.source,
                method=cv.method,
            )
            order.append(val_str)
        else:
            merged_dict[val_str] = merge_scalar_values(merged_dict[val_str], cv)

    return [merged_dict[val] for val in order]


def merge_skills(
    list_a: List[CandidateValue], list_b: List[CandidateValue]
) -> List[CandidateValue]:
    """
    Deduplicates and merges two lists of CandidateValue skills.
    """
    return _merge_candidate_value_list(list_a, list_b)


def merge_experience(
    list_a: List[ExperienceEntry], list_b: List[ExperienceEntry]
) -> List[ExperienceEntry]:
    """
    Deduplicates and merges two lists of ExperienceEntry.
    Deduplication key is: normalized(company) + normalized(title).

    Args:
        list_a: First list of experiences.
        list_b: Second list of experiences.

    Returns:
        A new list of ExperienceEntry representing the merged union.
    """
    merged_entries = {}
    order = []

    lst_a = list_a if list_a else []
    lst_b = list_b if list_b else []

    for entry in lst_a + lst_b:
        if not entry:
            continue

        comp_str = (
            entry.company.value
            if (entry.company and entry.company.value is not None)
            else ""
        )
        title_str = (
            entry.title.value
            if (entry.title and entry.title.value is not None)
            else ""
        )
        key = _normalize_str_for_key(comp_str) + "|" + _normalize_str_for_key(title_str)

        if key not in merged_entries:
            new_comp = (
                CandidateValue(
                    entry.company.value,
                    entry.company.confidence,
                    entry.company.source,
                    entry.company.method,
                )
                if entry.company
                else None
            )
            new_title = (
                CandidateValue(
                    entry.title.value,
                    entry.title.confidence,
                    entry.title.source,
                    entry.title.method,
                )
                if entry.title
                else None
            )
            new_start = (
                CandidateValue(
                    entry.start.value,
                    entry.start.confidence,
                    entry.start.source,
                    entry.start.method,
                )
                if entry.start
                else None
            )
            new_end = (
                CandidateValue(
                    entry.end.value,
                    entry.end.confidence,
                    entry.end.source,
                    entry.end.method,
                )
                if entry.end
                else None
            )

            merged_entries[key] = ExperienceEntry(
                company=new_comp,
                title=new_title,
                start=new_start,
                end=new_end,
            )
            order.append(key)
        else:
            existing = merged_entries[key]
            existing.company = merge_scalar_values(existing.company, entry.company)
            existing.title = merge_scalar_values(existing.title, entry.title)
            existing.start = merge_scalar_values(existing.start, entry.start)
            existing.end = merge_scalar_values(existing.end, entry.end)

    return [merged_entries[k] for k in order]


def merge_education(
    list_a: List[EducationEntry], list_b: List[EducationEntry]
) -> List[EducationEntry]:
    """
    Deduplicates and merges two lists of EducationEntry.
    Deduplication key is: normalized(institution) + normalized(degree).

    Args:
        list_a: First list of educations.
        list_b: Second list of educations.

    Returns:
        A new list of EducationEntry representing the merged union.
    """
    merged_entries = {}
    order = []

    lst_a = list_a if list_a else []
    lst_b = list_b if list_b else []

    for entry in lst_a + lst_b:
        if not entry:
            continue

        inst_str = (
            entry.institution.value
            if (entry.institution and entry.institution.value is not None)
            else ""
        )
        deg_str = (
            entry.degree.value
            if (entry.degree and entry.degree.value is not None)
            else ""
        )
        key = _normalize_str_for_key(inst_str) + "|" + _normalize_str_for_key(deg_str)

        if key not in merged_entries:
            new_inst = (
                CandidateValue(
                    entry.institution.value,
                    entry.institution.confidence,
                    entry.institution.source,
                    entry.institution.method,
                )
                if entry.institution
                else None
            )
            new_deg = (
                CandidateValue(
                    entry.degree.value,
                    entry.degree.confidence,
                    entry.degree.source,
                    entry.degree.method,
                )
                if entry.degree
                else None
            )
            new_end = (
                CandidateValue(
                    entry.end.value,
                    entry.end.confidence,
                    entry.end.source,
                    entry.end.method,
                )
                if entry.end
                else None
            )

            merged_entries[key] = EducationEntry(
                institution=new_inst,
                degree=new_deg,
                end=new_end,
            )
            order.append(key)
        else:
            existing = merged_entries[key]
            existing.institution = merge_scalar_values(existing.institution, entry.institution)
            existing.degree = merge_scalar_values(existing.degree, entry.degree)
            existing.end = merge_scalar_values(existing.end, entry.end)

    return [merged_entries[k] for k in order]


def _collect_confidences(candidate: Candidate) -> List[float]:
    """
    Collects the confidence values of all non-null final CandidateValue objects.
    """
    confidences = []

    def add_cv(cv: Optional[CandidateValue]):
        if cv is not None and cv.value is not None:
            confidences.append(cv.confidence)

    # Scalar fields
    add_cv(candidate.full_name)
    add_cv(candidate.headline)
    add_cv(candidate.years_experience)
    add_cv(candidate.location)

    # Lists of CandidateValue
    for list_field in (candidate.emails, candidate.phones, candidate.skills, candidate.links):
        if list_field:
            for cv in list_field:
                add_cv(cv)

    # Nested experience values
    if candidate.experience:
        for exp in candidate.experience:
            if exp:
                add_cv(exp.company)
                add_cv(exp.title)
                add_cv(exp.start)
                add_cv(exp.end)

    # Nested education values
    if candidate.education:
        for edu in candidate.education:
            if edu:
                add_cv(edu.institution)
                add_cv(edu.degree)
                add_cv(edu.end)

    return confidences


def merge_candidates(candidate_a: Candidate, candidate_b: Candidate) -> Candidate:
    """
    Merge two candidate profiles into a single consolidated Candidate profile.
    Inputs are not mutated; a completely new Candidate is returned.
    """
    # 1. Merge scalar fields
    full_name = merge_scalar_values(candidate_a.full_name, candidate_b.full_name)
    headline = merge_scalar_values(candidate_a.headline, candidate_b.headline)
    years_experience = merge_scalar_values(
        candidate_a.years_experience, candidate_b.years_experience
    )
    location = merge_scalar_values(candidate_a.location, candidate_b.location)

    # 2. Merge list fields
    emails = _merge_candidate_value_list(candidate_a.emails, candidate_b.emails)
    phones = _merge_candidate_value_list(candidate_a.phones, candidate_b.phones)
    skills = merge_skills(candidate_a.skills, candidate_b.skills)
    links = _merge_candidate_value_list(candidate_a.links, candidate_b.links)

    # 3. Merge experience & education
    experience = merge_experience(candidate_a.experience, candidate_b.experience)
    education = merge_education(candidate_a.education, candidate_b.education)

    # Construct new Candidate
    merged_cand = Candidate(
        candidate_id="",
        full_name=full_name,
        emails=emails,
        phones=phones,
        location=location,
        links=links,
        headline=headline,
        years_experience=years_experience,
        skills=skills,
        experience=experience,
        education=education,
        overall_confidence=0.0,
    )

    # Calculate overall confidence
    confs = _collect_confidences(merged_cand)
    if confs:
        merged_cand.overall_confidence = round(sum(confs) / len(confs), 2)
    else:
        merged_cand.overall_confidence = 0.0

    return merged_cand
