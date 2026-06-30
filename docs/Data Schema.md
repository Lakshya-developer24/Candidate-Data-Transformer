# Data Schemas & Worked Example

## Project

**Project Name:** Multi Source Candidate Data Transformer

**Purpose:** This document resolves every exact shape referenced by
`PRD.md`, `Tech Stack.md`, and `System architecture.md` —
CLI flags, config schema, input schemas, output schemas, and a single
worked example traced end-to-end through every pipeline stage with
real computed values. Where this document and the others differ on a
specific value, this document wins.

**Status:** Frozen v1 — ready for implementation

------------------------------------------------------------------------

# 1. CLI Specification

```
candidate-transformer --csv PATH --resumes PATH [--config PATH] [--out PATH]
```

| Flag         | Required | Default     | Description                                  |
|--------------|----------|-------------|-----------------------------------------------|
| `--csv`      | yes      | —           | Path to the recruiter CSV file                |
| `--resumes`  | yes      | —           | Path to a directory of resume `.txt` files     |
| `--config`   | no       | built-in default (see §3) | Path to `config.json`          |
| `--out`      | no       | `./output`  | Output directory for the two JSON files       |
| `-h, --help` | no       | —           | Show usage and exit                            |

On completion, the CLI prints a one-line summary to stdout, e.g.:

```
Processed 42 candidates: 39 succeeded, 3 failed. See output/profiles.json and output/failed_candidates.json.
```

------------------------------------------------------------------------

# 2. Recruiter CSV Schema

Exact header row (column order is not significant, names are):

```
name,email,phone,company,title
```

| Column   | Required | Notes                                              |
|----------|----------|------------------------------------------------------|
| `name`   | yes      | Full name, free text                                  |
| `email`  | no       | Used as the default matching key when present          |
| `phone`  | no       | Any common format; normalized to E.164 during extraction |
| `company`| no       | Current employer; becomes one experience entry with `start`/`end = null` |
| `title`  | no       | Current title; paired with `company` as above           |

A row missing `name` is treated as a malformed record and routed to
`failed_candidates.json` at the Reader/Extractor stage.

------------------------------------------------------------------------

# 3. config.json Schema

```json
{
  "fields": [
    { "from": "<canonical path>", "to": "<output key>", "normalize": "<optional override>" }
  ],
  "include_confidence": true,
  "include_provenance": true,
  "on_missing": "null"
}
```

| Key                   | Type    | Notes                                                          |
|------------------------|---------|------------------------------------------------------------------|
| `fields`               | array   | Ordered list of field selections. If omitted, all canonical fields are selected. |
| `fields[].from`        | string  | Canonical path. Supported shapes only: a bare field name (`full_name`), `emails[0]`, `phones[0]`, `skills[].name`, `experience[].company`, `experience[].title`, `experience[].start`, `experience[].end`, `education[].institution`, `education[].degree`. |
| `fields[].to`          | string  | Output key name. Defaults to `from` if omitted.                  |
| `fields[].normalize`   | string  | Optional per-field override (e.g. force a date to year-only). Optional — omit unless needed. |
| `include_confidence`   | bool    | Default `true`. Adds a `confidence` value alongside each projected field. |
| `include_provenance`   | bool    | Default `true`. Adds `source`/`method` alongside each projected field. |
| `on_missing`           | string  | One of `"null"` (default), `"omit"`, `"error"`.                  |

**Built-in default config** (used when `--config` is not passed):
`fields` omitted (→ all canonical fields), `include_confidence: true`,
`include_provenance: true`, `on_missing: "null"`.

------------------------------------------------------------------------

# 4. Resume Section Headers

Section detection matches a line (case-insensitive, after stripping
whitespace and trailing colons) against the following recognized
headers. Everything between one recognized header and the next belongs
to that section.

| Canonical section | Recognized header strings                                  |
|--------------------|--------------------------------------------------------------|
| `summary`          | SUMMARY, PROFILE, OBJECTIVE                                   |
| `skills`           | SKILLS, TECHNICAL SKILLS, CORE COMPETENCIES                    |
| `experience`       | EXPERIENCE, WORK EXPERIENCE, EMPLOYMENT HISTORY, PROFESSIONAL EXPERIENCE |
| `education`        | EDUCATION, ACADEMIC BACKGROUND                                  |
| `contact`          | CONTACT, CONTACT INFORMATION                                    |

Lines before the first recognized header are treated as the resume
header block:

- **Line 1** (first non-blank line) → candidate full name,
  `method = "resume_regex"`.
- **Line 2**, only if it appears before any recognized section header
  → headline, `method = "resume_inferred"`.

------------------------------------------------------------------------

# 5. Resume Field Extraction Rules

| Field              | Section     | Technique                                                              | Method            |
|----------------------|-------------|---------------------------------------------------------------------------|--------------------|
| `full_name`         | header block | first non-blank line                                                     | `resume_regex`     |
| `headline`          | header block | second non-blank line (if before any section header)                      | `resume_inferred`  |
| `email`             | `contact`    | standard email regex                                                      | `resume_regex`     |
| `phone`             | `contact`    | phone-number regex, normalized to E.164                                   | `resume_regex`     |
| `skills`            | `skills`     | split on commas/newlines, each token canonicalized via alias dict          | `resume_keyword`   |
| `experience`        | `experience` | regex on `"Company — Title"` line + date-range regex (`Mon YYYY - Mon YYYY|Present`) on the following line | `resume_regex`     |
| `education`         | `education`  | regex on `"Degree, Institution, Year"` line                               | `resume_regex`     |
| `years_experience`  | `summary`    | regex `(\d+)\+?\s+years` against summary text                              | `resume_inferred`  |

Skill alias dictionary lives in `normalization.py` (per
`02_TECH_STACK.md`). Example entries: `"JS" → "JavaScript"`,
`"K8s" → "Kubernetes"`, `"Postgres" → "PostgreSQL"`.

------------------------------------------------------------------------

# 6. Internal Model — Exact Shapes

## CandidateValue

```json
{ "value": "...", "confidence": 0.0, "source": "...", "method": "..." }
```

`source` is a string for single-source values, or a list of two
strings (e.g. `["recruiter_csv", "resume_txt"]`) when `method ==
"agreed"`.

## Experience entry

Not a single `CandidateValue` — a dict of per-field `CandidateValue`
objects, since each sub-field can independently agree, conflict, or
come from only one source:

```json
{
  "company": CandidateValue,
  "title": CandidateValue,
  "start": CandidateValue,
  "end": CandidateValue
}
```

## Education entry

Same pattern:

```json
{
  "institution": CandidateValue,
  "degree": CandidateValue,
  "end": CandidateValue
}
```

## Skills entry

A skill has no sub-fields, so each list entry is a plain
`CandidateValue` whose `value` is the canonical skill name string.

## Canonical Candidate (full, unprojected)

```json
{
  "candidate_id": "cand_xxxxxxxxxxxx",
  "full_name": CandidateValue,
  "emails": [CandidateValue],
  "phones": [CandidateValue],
  "location": CandidateValue,
  "links": CandidateValue,
  "headline": CandidateValue,
  "years_experience": CandidateValue,
  "skills": [CandidateValue],
  "experience": [ExperienceEntry],
  "education": [EducationEntry],
  "overall_confidence": 0.0
}
```

Unextracted scalar fields (e.g. `location`, `links` when nothing was
found) are `null`, not omitted, at the canonical level. Omission only
happens at Projection, per `on_missing`.

------------------------------------------------------------------------

# 7. failed_candidates.json Shape

```json
[
  {
    "identifier": "cand_xxxxxxxxxxxx",
    "source": "csv_row:5",
    "stage": "validation",
    "reason": "required field 'email' missing after projection"
  }
]
```

`source` is either `csv_row:<row_index>`, `resume_file:<filename>`, or
both (`csv_row:5+resume_file:jane_doe.txt`) for matched pairs that
failed after matching. `identifier` is the best available
`candidate_id`, or a placeholder like `unidentified_row_5` if ID
derivation itself was the failure point.

------------------------------------------------------------------------

# 8. Worked Example

## 8.1 Input — Recruiter CSV row

```csv
name,email,phone,company,title
Jane Doe,Jane.Doe@Example.com,(415) 555-0199,Acme Corp,Senior Software Engineer
```

## 8.2 Input — Resume (`jane_doe.txt`)

```
Jane Doe
Senior Backend Engineer

SUMMARY
Backend engineer with 6 years of experience building distributed systems.

SKILLS
Python, AWS, Docker, Kubernetes, JS

EXPERIENCE
Acme Corp — Senior Software Engineer
Jan 2021 - Present

Globex Inc — Software Engineer
Jun 2018 - Dec 2020

EDUCATION
B.S. Computer Science, State University, 2018

CONTACT
jane.doe@example.com
+1 415 555 0199
```

## 8.3 Matching

Normalized CSV email (`jane.doe@example.com`) matches the email found
in the resume's `contact` section → matched pair, single candidate.

## 8.4 Candidate ID

```
normalized_primary_email = "jane.doe@example.com"
sha256(...)               = 86e0b9e56c17cc4d12387e1949b85053fbe73bc3ce5a1188713a9d300cc6133d
candidate_id               = "cand_86e0b9e56c17"
```

(Computed directly with Python's `hashlib` — verify your
implementation reproduces this exact value.)

## 8.5 Extraction (before normalization/merge)

CSV → `csv_direct`, confidence 0.95: `full_name="Jane Doe"`,
`email="Jane.Doe@Example.com"`, `phone="(415) 555-0199"`, one
experience entry (`company="Acme Corp"`, `title="Senior Software
Engineer"`, `start=null`, `end=null`).

Resume → `full_name="Jane Doe"` (`resume_regex`, 0.80),
`headline="Senior Backend Engineer"` (`resume_inferred`, 0.60),
`years_experience=6` (`resume_inferred`, 0.60),
`email="jane.doe@example.com"` (`resume_regex`, 0.80),
`phone="+1 415 555 0199"` (`resume_regex`, 0.80),
`skills=["Python","AWS","Docker","Kubernetes","JS"]` (`resume_keyword`,
0.80 each), two experience entries (Acme Corp/Senior Software
Engineer/Jan 2021–Present; Globex Inc/Software Engineer/Jun 2018–Dec
2020, both `resume_regex`, 0.80), one education entry (State
University/B.S. Computer Science/2018, `resume_regex`, 0.80).

## 8.6 Normalization

`Jane.Doe@Example.com` → `jane.doe@example.com`.
`(415) 555-0199` and `+1 415 555 0199` → both `+14155550199`.
`Jan 2021` → `2021-01`; `Present` → `null`; `Jun 2018` → `2018-06`;
`Dec 2020` → `2020-12`; graduation `2018` → `2018-01`.
`JS` → `JavaScript` (alias dict).

## 8.7 Merge

`full_name`: CSV (0.95) and resume (0.80) agree on `"Jane Doe"` →
**agreed**, confidence `min(1.0, 0.95+0.05) = 1.0`.

`emails[0]`: both normalize to `jane.doe@example.com` → agreed,
confidence `1.0`.

`phones[0]`: both normalize to `+14155550199` → agreed, confidence
`1.0`.

`headline`: resume-only → `"Senior Backend Engineer"`, confidence
`0.60`, method `resume_inferred`.

`years_experience`: resume-only → `6`, confidence `0.60`, method
`resume_inferred`.

`skills`: resume-only, 5 entries, each confidence `0.80`.

`experience`: CSV's Acme Corp/Senior Software Engineer entry shares a
dedupe key with the resume's first entry → merged field-by-field:
`company` agreed (1.0), `title` agreed (1.0), `start` resume-only
(`2021-01`, 0.80), `end` both null. The Globex Inc entry has no CSV
counterpart → stands alone, all fields at `0.80`.

`education`: resume-only, all fields at `0.80`.

## 8.8 overall_confidence

Mean of every non-null final field confidence (21 values total: 1
full_name + 1 headline + 1 years_experience + 1 email + 1 phone + 5
skills + 3 non-null Acme fields + 4 Globex fields + 3 education
fields):

```
(1.00 + 0.60 + 0.60 + 1.00 + 1.00 + 0.80×5 + (1.00+1.00+0.80) + (0.80×4) + (0.80×3)) / 21
= 16.60 / 21
= 0.7905 → 0.79
```

## 8.9 Output — `profiles.json` entry (default config, unprojected shape)

```json
{
  "candidate_id": "cand_86e0b9e56c17",
  "full_name": { "value": "Jane Doe", "confidence": 1.0, "source": ["recruiter_csv", "resume_txt"], "method": "agreed" },
  "emails": [
    { "value": "jane.doe@example.com", "confidence": 1.0, "source": ["recruiter_csv", "resume_txt"], "method": "agreed" }
  ],
  "phones": [
    { "value": "+14155550199", "confidence": 1.0, "source": ["recruiter_csv", "resume_txt"], "method": "agreed" }
  ],
  "location": null,
  "links": null,
  "headline": { "value": "Senior Backend Engineer", "confidence": 0.60, "source": "resume_txt", "method": "resume_inferred" },
  "years_experience": { "value": 6, "confidence": 0.60, "source": "resume_txt", "method": "resume_inferred" },
  "skills": [
    { "value": "Python", "confidence": 0.80, "source": "resume_txt", "method": "resume_keyword" },
    { "value": "AWS", "confidence": 0.80, "source": "resume_txt", "method": "resume_keyword" },
    { "value": "Docker", "confidence": 0.80, "source": "resume_txt", "method": "resume_keyword" },
    { "value": "Kubernetes", "confidence": 0.80, "source": "resume_txt", "method": "resume_keyword" },
    { "value": "JavaScript", "confidence": 0.80, "source": "resume_txt", "method": "resume_keyword" }
  ],
  "experience": [
    {
      "company": { "value": "Acme Corp", "confidence": 1.0, "source": ["recruiter_csv", "resume_txt"], "method": "agreed" },
      "title": { "value": "Senior Software Engineer", "confidence": 1.0, "source": ["recruiter_csv", "resume_txt"], "method": "agreed" },
      "start": { "value": "2021-01", "confidence": 0.80, "source": "resume_txt", "method": "resume_regex" },
      "end": null
    },
    {
      "company": { "value": "Globex Inc", "confidence": 0.80, "source": "resume_txt", "method": "resume_regex" },
      "title": { "value": "Software Engineer", "confidence": 0.80, "source": "resume_txt", "method": "resume_regex" },
      "start": { "value": "2018-06", "confidence": 0.80, "source": "resume_txt", "method": "resume_regex" },
      "end": { "value": "2020-12", "confidence": 0.80, "source": "resume_txt", "method": "resume_regex" }
    }
  ],
  "education": [
    {
      "institution": { "value": "State University", "confidence": 0.80, "source": "resume_txt", "method": "resume_regex" },
      "degree": { "value": "B.S. Computer Science", "confidence": 0.80, "source": "resume_txt", "method": "resume_regex" },
      "end": { "value": "2018-01", "confidence": 0.80, "source": "resume_txt", "method": "resume_regex" }
    }
  ],
  "overall_confidence": 0.79
}
```

## 8.10 Output — same candidate, projected with an example config.json

```json
{
  "fields": [
    { "from": "full_name", "to": "name" },
    { "from": "emails[0]", "to": "email" },
    { "from": "phones[0]", "to": "phone" },
    { "from": "headline", "to": "headline" },
    { "from": "skills[].name", "to": "skills" },
    { "from": "experience[].company", "to": "companies" }
  ],
  "include_confidence": true,
  "include_provenance": false,
  "on_missing": "null"
}
```

Resulting `profiles.json` entry:

```json
{
  "candidate_id": "cand_86e0b9e56c17",
  "name": { "value": "Jane Doe", "confidence": 1.0 },
  "email": { "value": "jane.doe@example.com", "confidence": 1.0 },
  "phone": { "value": "+14155550199", "confidence": 1.0 },
  "headline": { "value": "Senior Backend Engineer", "confidence": 0.60 },
  "skills": [
    { "value": "Python", "confidence": 0.80 },
    { "value": "AWS", "confidence": 0.80 },
    { "value": "Docker", "confidence": 0.80 },
    { "value": "Kubernetes", "confidence": 0.80 },
    { "value": "JavaScript", "confidence": 0.80 }
  ],
  "companies": [
    { "value": "Acme Corp", "confidence": 1.0 },
    { "value": "Globex Inc", "confidence": 0.80 }
  ]
}
```

`candidate_id` is always included regardless of `fields`, since it is
the record's primary key — it is not subject to selection/renaming.

------------------------------------------------------------------------

# 9. Acceptance Check

An implementation is considered correct for this worked example if,
given the CSV row and resume file in §8.1–8.2 and no `--config` flag,
it produces byte-for-byte the JSON in §8.9 (modulo key ordering), and
produces the JSON in §8.10 when run with the config in §8.10. This is
the canonical integration test referenced in `02_TECH_STACK.md` §10.