# Candidate Data Transformer

## Overview

This is a command-line application that transforms recruiter CSV data and resume text files into consolidated candidate profiles through extraction, normalization, matching, merging, projection, and validation. The tool matches candidate records across multiple input sources, reconciles duplicate or conflicting data based on confidence metrics, and outputs clean candidate JSON profiles.

---

## Requirements

- Python 3.8 or higher
- Standard library modules only (no external library dependencies)

---

## Installation

```bash
git clone <repository-url>
cd candidate-data-transformer
```

---

## Project Structure

candidate-data-transformer/
├── candidate_transformer/
├── configs/
├── docs/
├── input/
│   ├── recruiter/
│   └── resumes/
├── output/
└── tests/

---

## Input Format

### Recruiter CSV

The recruiter CSV export must contain candidate rows with headers representing candidate properties.

Expected columns:
- `name`: Candidate's full name.
- `email`: Candidate's primary email address (used for matching).
- `phone`: Candidate's contact phone number.
- `company`: Latest employer company name.
- `title`: Latest job title.

Sample CSV content:
```csv
name,email,phone,company,title
Jane Doe,Jane.Doe@Example.com,(415) 555-0199,Acme Corp,Senior Software Engineer
```

### Resume Files

- Resumes must be UTF-8 encoded text files with the extension `.txt`.
- There must be exactly one candidate's resume per file.

Sample resume content (`jane.txt`):
```text
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
+91 415 555 0199
```

### Configuration File

The configuration file is optional. It controls field filtering, key renaming, confidence metrics inclusion, provenance metadata mapping, and missing-value validation behavior.

Sample config.json:
```json
{
  "fields": [
    {
      "from": "full_name",
      "to": "name"
    },
    {
      "from": "emails[0]",
      "to": "email"
    },
    {
      "from": "skills",
      "to": "skills"
    }
  ],
  "include_confidence": false,
  "include_provenance": false,
  "on_missing": "null"
}
```

---

## Running the Project

```bash
python3 -m candidate_transformer.cli \
    --csv input/recruiter/recruiter.csv \
    --resumes input/resumes \
    --config configs/default.json \
    --out output
```

---

## Sample Run

Terminal output:
```text
Processed 2 candidates: 1 succeeded, 1 failed. See output/profiles.json and output/failed_candidates.json.
```

---

## Sample Output

Sample `profiles.json` (projected candidate output):
```json
[
  {
    "candidate_id": "cand_b722d3e18a99",
    "name": "Jane Doe",
    "email": "jane.doe@example.com",
    "skills": [
      "Python",
      "AWS",
      "Docker",
      "Kubernetes",
      "JavaScript"
    ]
  }
]
```

Sample `failed_candidates.json` (isolated failures output):
```json
[
  {
    "identifier": "bad@example.com",
    "source": "recruiter_csv",
    "stage": "extraction",
    "reason": "CSV candidate name is missing"
  }
]
```

---

## Output Files

- `profiles.json`: Stores the successfully processed, merged, projected, and validated candidate profiles.
- `failed_candidates.json`: Stores candidate-level processing failures containing failure stage and details.

---

## Running the Tests

```bash
python3 -m unittest discover -s tests/unit

python3 -m unittest discover -s tests/integration
```

---

## Notes

- Resume files must be `.txt` UTF-8 formatted text files.
- Candidate IDs are generated automatically using sha256 hashes of identifiers.
- Output files are recreated on every run.
- Empty runtime directories are preserved using `.gitkeep`.
- Configuration controls projected output fields.
