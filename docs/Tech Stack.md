# Technology Stack

## Project

**Project Name:** Multi Source Candidate Data Transformer

**Application Type:** Command Line Application (CLI)

**Status:** Frozen v1 — ready for implementation

------------------------------------------------------------------------

# 1. Technology Stack Philosophy

The technology stack has been intentionally kept minimal.

The objective of this project is to demonstrate data transformation,
software architecture, modular design, and deterministic processing
rather than the use of numerous third-party libraries.

Wherever possible, the Python Standard Library is preferred over
external dependencies.

Design principles:

- Standard library first
- Minimal dependencies
- Deterministic execution
- Readability over cleverness
- Modular architecture
- Easy testing
- Easy future extension

------------------------------------------------------------------------

# 2. Programming Language

## Python 3

Python is selected because it provides:

- Excellent text processing capabilities
- Mature standard library
- Strong support for file handling
- Simple JSON processing
- Easy regular expression support
- Rapid development
- Cross-platform compatibility

Python is well suited for ETL (Extract, Transform, Load) style
applications where most operations involve parsing, transformation,
validation, and serialization.

------------------------------------------------------------------------

# 3. Standard Library Modules

## csv

Purpose

- Read recruiter CSV files
- Parse structured candidate records using `csv.DictReader`, keyed on
  the column headers defined in `04_DATA_SCHEMAS_AND_EXAMPLES.md`

Why

- Built into Python
- Reliable
- Handles quoted fields correctly
- No external dependency

------------------------------------------------------------------------

## pathlib

Purpose

- File and directory handling
- Resume discovery (iterating `*.txt` files in the resume directory)
- Cross-platform path manipulation
- Building output paths under the configured output directory

------------------------------------------------------------------------

## json

Purpose

- Read `config.json` (runtime configuration)
- Serialize final output
- Write `profiles.json`
- Write `failed_candidates.json`

------------------------------------------------------------------------

## re

Purpose

- Email extraction
- Phone extraction
- Date parsing
- Resume section-header detection (splitting raw resume text into
  named sections before keyword/field extraction)
- Keyword extraction within sections

Rule-based extraction depends heavily on regular expressions. The exact
section-header patterns recognized are listed in
`04_DATA_SCHEMAS_AND_EXAMPLES.md` so extraction behavior is reproducible.

------------------------------------------------------------------------

## hashlib

Purpose

Generate deterministic `candidate_id` values using SHA-256, per the
derivation rule (primary email, with documented fallbacks) defined in
`03_SYSTEM_ARCHITECTURE.md`.

------------------------------------------------------------------------

## argparse

Purpose

Implement the command-line interface.

Responsibilities:

- Parsing CLI arguments (`--csv`, `--resumes`, `--config`, `--out`,
  etc. — exact flags in `04_DATA_SCHEMAS_AND_EXAMPLES.md`)
- Validating required inputs (CSV path, resume directory)
- Displaying help information

------------------------------------------------------------------------

## dataclasses

Purpose

Implement the `Candidate` and `CandidateValue` models.

Benefits:

- Less boilerplate
- Readable models
- Easy serialization
- Type-safe structure

------------------------------------------------------------------------

## typing

Purpose

Improve code readability and maintainability through explicit type
hints.

------------------------------------------------------------------------

# 4. External Dependencies

No mandatory third-party libraries are required.

This keeps the project:

- Lightweight
- Easy to run
- Easy to review
- Easy to reproduce

The complete transformation pipeline can be implemented using Python's
standard library.

------------------------------------------------------------------------

# 5. Runtime Configuration

The application uses a JSON configuration file (`config.json`).

Responsibilities:

- Select output fields
- Rename fields
- Apply a per-field normalization override
- Configure missing-value behavior (`null` / `omit` / `error`)
- Toggle confidence output
- Toggle provenance output

Configuration affects only the projected output and never modifies the
canonical candidate.

The exact config schema and a worked example are defined in
`04_DATA_SCHEMAS_AND_EXAMPLES.md`.

------------------------------------------------------------------------

# 6. Input Formats

## Recruiter CSV

Structured input containing multiple candidate records, with a fixed
column schema (exact header row in `04_DATA_SCHEMAS_AND_EXAMPLES.md`).

Fields include:

- Name
- Email
- Phone
- Company
- Title

------------------------------------------------------------------------

## Resume TXT

Plain UTF-8 text files, one per candidate, in a single resume
directory.

Information is extracted using:

- Section-header detection
- Regular expressions
- Keyword matching

No OCR, NLP, or LLM processing is used.

------------------------------------------------------------------------

# 7. Output Formats

The application produces JSON.

Generated files:

- `output/profiles.json`
- `output/failed_candidates.json`

JSON is chosen because it is:

- Human readable
- Machine readable
- Widely supported
- Easy to validate

Exact output shapes, including how `CandidateValue` metadata nests
under each field, are defined in `04_DATA_SCHEMAS_AND_EXAMPLES.md`.

------------------------------------------------------------------------

# 8. Development Principles

The implementation follows these principles:

- Single Responsibility Principle
- Separation of Concerns
- Deterministic Processing
- Modular Components
- Reusable Pipeline Stages
- Canonical Internal Representation
- Configuration Driven Output

------------------------------------------------------------------------

# 9. Module / File Layout

```
candidate_transformer/
├── cli.py                  # argparse entrypoint, run summary printing
├── config.py                # config.json loading + validation
├── matcher.py                # CandidateMatcher interface + default impl
├── readers/
│   ├── csv_reader.py          # raw CSV row reading
│   └── resume_reader.py       # raw resume text reading
├── extractors/
│   ├── csv_extractor.py       # CSV row -> CandidateValue objects
│   └── resume_extractor.py    # resume text -> CandidateValue objects
│       (section splitting, regex/keyword extraction)
├── normalization.py          # email/phone/date/skill normalizers
├── merge.py                  # scalar + list-field merge logic
├── models.py                  # CandidateValue, Candidate dataclasses
├── projection.py             # config-driven output projection
├── validation.py              # post-projection validation
├── pipeline.py                # orchestrates one candidate end-to-end
├── batch.py                   # loops candidates, isolates failures,
│                               writes profiles.json / failed_candidates.json
└── id_generator.py           # candidate_id derivation (hashlib)

tests/
├── unit/                      # one test module per component above
└── integration/                # full-pipeline tests using the worked
                                  example in 04_DATA_SCHEMAS_AND_EXAMPLES.md
```

This layout maps one-to-one onto the pipeline stages in
`03_SYSTEM_ARCHITECTURE.md`, so each module has exactly one
responsibility and can be unit tested in isolation.

------------------------------------------------------------------------

# 10. Testing Strategy

The chosen stack enables testing at multiple levels.

## Unit Tests

- Readers
- Extractors (including section-header detection)
- Normalizers
- Merge logic (scalar winner-take-all, list dedupe-key union)
- Projection (path resolution, missing-value behavior)
- Validation
- `candidate_id` derivation (including fallback paths)

## Integration Tests

Complete candidate processing pipeline, including the worked example
in `04_DATA_SCHEMAS_AND_EXAMPLES.md` as a golden-output test.

## Batch Tests

Processing multiple candidates while isolating failures (e.g. one
malformed CSV row should not prevent other candidates from succeeding).

------------------------------------------------------------------------

# 11. Future Technology Extensions (Not Included)

Possible future additions include:

- PDF parsing libraries
- ATS JSON readers
- Database support
- REST API framework
- Web interface
- Containerization
- Cloud deployment
- Additional input adapters
- General-purpose JSONPath library for projection

These technologies are intentionally excluded from the current
implementation to keep the project focused on the assignment
requirements.