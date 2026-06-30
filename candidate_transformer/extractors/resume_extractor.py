"""
Module: candidate_transformer.extractors.resume_extractor

Extracts and structures information from unstructured resume text into Candidate data models.
Processes the text by detecting sections and applying regex and keyword extraction rules.
"""

import re
from typing import Dict, List, Optional
from candidate_transformer.models import (
    Candidate,
    CandidateValue,
    EducationEntry,
    ExperienceEntry,
)


class ResumeExtractor:
    """
    Extractor for parsing candidate properties from unstructured resume text.
    """

    def extract_from_text(self, text: str) -> Candidate:
        """
        Parse raw resume text using heuristics/regex/AI models and map it to a Candidate profile.

        Args:
            text: Raw resume text string.

        Returns:
            A populated Candidate model instance.

        Raises:
            ValueError: If the resume contains no readable content or candidate name cannot be derived.
        """
        if not text or not text.strip():
            raise ValueError("Resume text is empty or contains only whitespace")

        # Split text into lines and clean them
        lines = [line.strip() for line in text.splitlines()]

        # Section detection setup
        section_headers = {
            "summary": {"SUMMARY", "PROFILE", "OBJECTIVE"},
            "skills": {"SKILLS", "TECHNICAL SKILLS", "CORE COMPETENCIES"},
            "experience": {
                "EXPERIENCE",
                "WORK EXPERIENCE",
                "EMPLOYMENT HISTORY",
                "PROFESSIONAL EXPERIENCE",
            },
            "education": {"EDUCATION", "ACADEMIC BACKGROUND"},
            "contact": {"CONTACT", "CONTACT INFORMATION"},
        }

        # Segregate lines into header block and canonical sections
        sections: Dict[str, List[str]] = {
            "header": [],
            "summary": [],
            "skills": [],
            "experience": [],
            "education": [],
            "contact": [],
        }

        active_section = "header"

        for line in lines:
            # Check if this line is a section header
            # Section detection matches a line case-insensitively, after stripping whitespace and trailing colons
            clean_header = line.rstrip(":")
            clean_header_upper = clean_header.upper()

            matched_section = None
            for sec_name, headers in section_headers.items():
                if clean_header_upper in headers:
                    matched_section = sec_name
                    break

            if matched_section:
                active_section = matched_section
            else:
                sections[active_section].append(line)

        # 1. Header block parsing
        header_lines = [l for l in sections["header"] if l]
        if not header_lines:
            raise ValueError("No name or header block found in the resume")

        # First non-empty line -> full_name
        name_val = header_lines[0]
        full_name = CandidateValue(
            value=name_val,
            confidence=0.80,
            source="resume_txt",
            method="resume_regex",
        )

        # Second non-empty line before first recognized section -> headline
        headline = None
        if len(header_lines) > 1:
            headline_val = header_lines[1]
            headline = CandidateValue(
                value=headline_val,
                confidence=0.60,
                source="resume_txt",
                method="resume_inferred",
            )

        # 2. Summary parsing (years of experience)
        years_experience = None
        summary_text = " ".join([l for l in sections["summary"] if l])
        # regex (\d+)\+?\s+years against summary text
        match_years = re.search(r"(\d+)\+?\s+years", summary_text, re.IGNORECASE)
        if match_years:
            try:
                years_int = int(match_years.group(1))
                years_experience = CandidateValue(
                    value=years_int,
                    confidence=0.60,
                    source="resume_txt",
                    method="resume_inferred",
                )
            except ValueError:
                pass

        # 3. Contact parsing (emails and phones)
        emails = []
        phones = []
        contact_text = "\n".join(sections["contact"])

        # standard email regex
        email_pattern = re.compile(r"\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b")
        for match in email_pattern.finditer(contact_text):
            emails.append(
                CandidateValue(
                    value=match.group(1),
                    confidence=0.80,
                    source="resume_txt",
                    method="resume_regex",
                )
            )

        # phone-number regex
        phone_pattern = re.compile(r"(\+?\d[\d\s\-\(\)\.]{7,}\d)")
        for match in phone_pattern.finditer(contact_text):
            phones.append(
                CandidateValue(
                    value=match.group(1),
                    confidence=0.80,
                    source="resume_txt",
                    method="resume_regex",
                )
            )

        # 4. Skills parsing
        skills = []
        for line in sections["skills"]:
            if not line:
                continue
            # split on commas, then each token is a skill
            tokens = line.split(",")
            for token in tokens:
                skill_name = token.strip()
                if skill_name:
                    skills.append(
                        CandidateValue(
                            value=skill_name,
                            confidence=0.80,
                            source="resume_txt",
                            method="resume_keyword",
                        )
                    )

        # 5. Experience parsing
        experience = []
        exp_lines = [l for l in sections["experience"] if l]
        idx = 0
        while idx < len(exp_lines):
            line = exp_lines[idx]
            # Match "Company — Title" using standard dash separators
            match_job = re.match(r"^(.+?)\s*[-—–]\s*(.+)$", line)
            if match_job:
                company_str = match_job.group(1).strip()
                title_str = match_job.group(2).strip()
                start_str = None
                end_str = None

                # Check if the next line exists and matches a date range (Mon YYYY - Mon YYYY|Present)
                if idx + 1 < len(exp_lines):
                    next_line = exp_lines[idx + 1]
                    match_dates = re.match(
                        r"^([A-Za-z]{3}\s+\d{4})\s*[-—–]\s*([A-Za-z]{3}\s+\d{4}|Present)$",
                        next_line,
                        re.IGNORECASE,
                    )
                    if match_dates:
                        start_str = match_dates.group(1).strip()
                        end_str = match_dates.group(2).strip()
                        idx += 1  # consume date line

                comp_cv = CandidateValue(
                    value=company_str,
                    confidence=0.80,
                    source="resume_txt",
                    method="resume_regex",
                )
                title_cv = CandidateValue(
                    value=title_str,
                    confidence=0.80,
                    source="resume_txt",
                    method="resume_regex",
                )
                start_cv = (
                    CandidateValue(
                        value=start_str,
                        confidence=0.80,
                        source="resume_txt",
                        method="resume_regex",
                    )
                    if start_str
                    else None
                )
                end_cv = (
                    CandidateValue(
                        value=end_str,
                        confidence=0.80,
                        source="resume_txt",
                        method="resume_regex",
                    )
                    if end_str
                    else None
                )

                experience.append(
                    ExperienceEntry(
                        company=comp_cv,
                        title=title_cv,
                        start=start_cv,
                        end=end_cv,
                    )
                )
            idx += 1

        # 6. Education parsing
        education = []
        for line in sections["education"]:
            if not line:
                continue
            # regex on "Degree, Institution, Year" line
            match_edu = re.match(r"^([^,]+),\s*([^,]+),\s*(\d{4})$", line)
            if match_edu:
                degree_str = match_edu.group(1).strip()
                inst_str = match_edu.group(2).strip()
                year_str = match_edu.group(3).strip()

                inst_cv = CandidateValue(
                    value=inst_str,
                    confidence=0.80,
                    source="resume_txt",
                    method="resume_regex",
                )
                degree_cv = CandidateValue(
                    value=degree_str,
                    confidence=0.80,
                    source="resume_txt",
                    method="resume_regex",
                )
                end_cv = CandidateValue(
                    value=year_str,
                    confidence=0.80,
                    source="resume_txt",
                    method="resume_regex",
                )

                education.append(
                    EducationEntry(
                        institution=inst_cv,
                        degree=degree_cv,
                        end=end_cv,
                    )
                )

        return Candidate(
            candidate_id="",
            full_name=full_name,
            emails=emails,
            phones=phones,
            location=None,
            links=[],
            headline=headline,
            years_experience=years_experience,
            skills=skills,
            experience=experience,
            education=education,
            overall_confidence=0.0,
        )
