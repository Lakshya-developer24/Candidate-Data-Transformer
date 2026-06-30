"""
Module: candidate_transformer.models

This module defines the internal data representation models for candidates, including
individual data values, educational history, work experience, and consolidated profiles.
All models are implemented using standard Python dataclasses and include full type hints.
"""

from dataclasses import dataclass, field
from typing import Any, List


@dataclass
class CandidateValue:
    """
    Represents a specific candidate attribute value with metadata indicating its source,
    how it was extracted, and the extraction/matching confidence level.
    """
    value: Any
    confidence: float
    source: str
    method: str


@dataclass
class ExperienceEntry:
    """
    Represents an individual work experience entry. Each field is represented
    as a CandidateValue to track confidence, source, and extraction method.
    """
    company: CandidateValue
    title: CandidateValue
    start: CandidateValue
    end: CandidateValue


@dataclass
class EducationEntry:
    """
    Represents an individual education record. Each field is represented
    as a CandidateValue to track confidence, source, and extraction method.
    """
    institution: CandidateValue
    degree: CandidateValue
    end: CandidateValue


@dataclass
class Candidate:
    """
    Represents a consolidated candidate profile with aggregated contact details,
    work/educational histories, and overall data confidence score.
    """
    candidate_id: str
    full_name: CandidateValue
    emails: List[CandidateValue] = field(default_factory=list)
    phones: List[CandidateValue] = field(default_factory=list)
    location: CandidateValue = None
    links: List[CandidateValue] = field(default_factory=list)
    headline: CandidateValue = None
    years_experience: CandidateValue = None
    skills: List[CandidateValue] = field(default_factory=list)
    experience: List[ExperienceEntry] = field(default_factory=list)
    education: List[EducationEntry] = field(default_factory=list)
    overall_confidence: float = 0.0
