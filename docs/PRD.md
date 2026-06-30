# Product Requirements Document

## Project

**Project Name:** Multi Source Candidate Data Transformer

**Project Type:** Command Line Application (CLI)

**Status:** Frozen v1 — ready for implementation

------------------------------------------------------------------------

# 1. Introduction

The Multi Source Candidate Data Transformer is a backend data
transformation system that consolidates candidate information from
multiple heterogeneous sources into a single canonical candidate
profile.

The project focuses on deterministic data processing rather than user
interface development. It demonstrates how structured and unstructured
candidate information can be ingested, normalized, merged, validated,
and exported in a configurable format.

This document defines what the system must do. Implementation details
live in `02_TECH_STACK.md`, module design in `03_SYSTEM_ARCHITECTURE.md`,
and exact schemas/examples in `04_DATA_SCHEMAS_AND_EXAMPLES.md`.

------------------------------------------------------------------------

# 2. Problem Statement

Recruiters often collect candidate information from multiple sources.
Structured recruiter exports typically contain basic contact information
and employment details, while resumes contain richer information such as
education, work history, skills, and professional summaries.

These sources frequently contain:

- Missing information
- Duplicate information
- Different naming conventions
- Different formats
- Conflicting values

Without transformation, downstream systems cannot consume this
information consistently.

The objective of this project is to transform these heterogeneous inputs
into one clean, standardized candidate profile.

------------------------------------------------------------------------

# 3. Project Goals

The system shall:

- Read candidate information from a Recruiter CSV and a directory of
  Resume TXT files.
- Support batch processing of multiple candidates.
- Match candidate records deterministically (default: normalized
  primary email), via a swappable matching strategy.
- Extract structured information from both sources.
- Normalize values into consistent formats.
- Merge overlapping information using deterministic, documented rules.
- Track provenance for every retained value.
- Assign confidence values to extracted information, using a fixed
  confidence table per extraction method.
- Produce a single canonical candidate profile per candidate.
- Generate configurable JSON output.
- Continue processing when individual candidates fail.
- Print a final run summary (total processed, succeeded, failed).

------------------------------------------------------------------------

# 4. Project Scope

## In Scope

- Recruiter CSV input
- Resume TXT input
- Rule-based extraction (regex + section-header detection + keyword
  matching only — no NLP libraries, no LLM)
- Candidate matching (default: normalized email; swappable interface)
- Data normalization
- Record merging
- Provenance tracking
- Confidence calculation
- Runtime configurable output (via `config.json`)
- Validation
- Batch processing with per-candidate failure isolation
- CLI execution
- JSON output

## Out of Scope

- Web application
- Authentication
- Database
- REST APIs
- Cloud deployment
- Background workers
- Resume PDF support
- ATS JSON support
- LinkedIn integration
- GitHub integration
- OCR
- AI/LLM-based extraction
- Machine Learning
- General-purpose JSONPath / config path resolution (only the specific
  path shapes defined in `04_DATA_SCHEMAS_AND_EXAMPLES.md` are
  supported)

------------------------------------------------------------------------

# 5. Functional Requirements

## Input Sources

The application shall accept:

- One recruiter CSV containing multiple candidate records (exact column
  schema defined in `04_DATA_SCHEMAS_AND_EXAMPLES.md`).
- One directory containing resume `.txt` files.
- One optional runtime config JSON file (defaults apply if omitted).
- One output directory.

Exact CLI flags are defined in `04_DATA_SCHEMAS_AND_EXAMPLES.md`.

## Candidate Matching

The system shall associate recruiter records and resumes using a
deterministic matching strategy, implemented behind a swappable
`CandidateMatcher` interface.

Default strategy: match a CSV row to a resume file by normalized
primary email.

- Candidates without matching resumes (CSV-only) shall still be
  processed.
- Resume-only candidates shall also be processed; their identifying
  email is pulled from resume text for ID derivation.

## Information Extraction

The application shall extract:

- Name
- Email
- Phone
- Headline
- Skills
- Experience
- Education
- Current company
- Current title

Extraction from resumes shall be completely rule-based, using
section-header detection followed by regex/keyword extraction within
each detected section. The recognized section headers are defined in
`04_DATA_SCHEMAS_AND_EXAMPLES.md`.

Every extracted value is assigned a confidence score and a method label
at extraction time (see Confidence below) — not assigned or modified
later in the pipeline.

## Normalization

The application shall normalize:

- Email addresses → lowercased
- Phone numbers → E.164 format
- Dates → `YYYY-MM` format
- Skill names → canonical name via an in-code alias dictionary

Normalization only transforms `CandidateValue.value`. It never changes
confidence, source, or method, and never decides which of two
conflicting values wins — that is exclusively Merge's responsibility.

## Merge

The application shall merge all extracted information into a single
canonical candidate profile.

- **Scalar fields** (full name, individual email/phone, headline, years
  of experience) use winner-take-all by confidence. Equal normalized
  values from two sources become "agreed" with a confidence bonus.
  Exact ties favor the CSV-sourced value. The losing value is dropped,
  not stored.
- **List fields** (skills, experience, education) use dedupe-key union,
  not winner-take-all. Once two entries share a dedupe key, each field
  inside that entry is resolved independently using the same scalar
  rule.

Full merge rules and the confidence table are defined in
`03_SYSTEM_ARCHITECTURE.md` and `04_DATA_SCHEMAS_AND_EXAMPLES.md`.

## Provenance

Every retained value shall record:

- Source (e.g. `recruiter_csv`, `resume_txt`)
- Extraction method (e.g. `csv_direct`, `resume_regex`, `agreed`)

## Confidence

Every extracted value shall receive a confidence score determined by a
fixed table keyed on extraction method. An overall candidate confidence
score shall be computed after merging, as the mean of all non-null
final field confidences, rounded to 2 decimals.

## Canonical Candidate

Every candidate shall be represented internally using one canonical
data model (`Candidate`, composed of `CandidateValue` objects)
regardless of input source. All processing operates exclusively on this
canonical representation.

## Projection

The application shall support runtime configurable output via
`config.json`. Configuration may:

- Select fields
- Rename fields ("from" remap)
- Apply a per-field normalization override
- Toggle confidence output
- Toggle provenance output
- Control missing-value behavior (`null` / `omit` / `error`, the last
  deferred to Validation)

The projection layer supports only the specific path shapes defined in
`04_DATA_SCHEMAS_AND_EXAMPLES.md` (e.g. `emails[0]`, `skills[].name`,
`experience[].company`) — it is not a general path/query engine.

The canonical candidate shall never be modified during projection.

## Validation

Projected output shall be validated after projection, before
serialization. Validation shall ensure required fields are present and
correctly typed, respecting the configured missing-value behavior.
Validation failures affect only the current candidate.

## Batch Processing

Each candidate shall be processed independently, isolated from
failures elsewhere in the batch. Failure of one candidate shall not
stop the remaining batch.

## Output

The application shall generate:

- `output/profiles.json` — all successfully processed candidates
- `output/failed_candidates.json` — failed candidates with identifier
  and failure reason

The CLI shall print a final summary: total processed, succeeded,
failed.

## CLI

The application shall expose a command line interface for execution,
with required and optional arguments as defined in
`04_DATA_SCHEMAS_AND_EXAMPLES.md`.

------------------------------------------------------------------------

# 6. Non Functional Requirements

## Deterministic

The same input and configuration shall always produce the same output.

## Reliable

Invalid or failing candidates shall not terminate batch execution.

## Maintainable

Each pipeline stage shall have a single responsibility and a dedicated
module.

## Extensible

Future data sources shall require minimal changes outside new readers
and extractors, since all downstream stages operate on the canonical
model. Candidate matching is similarly swappable via interface.

## Scalable

The application shall reasonably process recruiter exports containing
thousands of candidates.

------------------------------------------------------------------------

# 7. Constraints

- Python implementation, standard library only (no mandatory
  third-party dependencies).
- CLI only.
- Recruiter CSV is the only structured source.
- Resume TXT is the only unstructured source.
- Rule-based extraction only — no NLP libraries, no LLM/AI services.
- No database.

------------------------------------------------------------------------

# 8. Assumptions

- Recruiter CSV follows the fixed schema defined in
  `04_DATA_SCHEMAS_AND_EXAMPLES.md`.
- Resume files are UTF-8 encoded plain text.
- Candidate matching information (typically email) is available for at
  least one source per candidate where possible.
- Runtime configuration, if provided, is valid JSON matching the
  documented schema.

------------------------------------------------------------------------

# 9. Error Handling Requirements

The application shall gracefully handle:

- Missing resumes (CSV-only candidates)
- Resume-only candidates (no matching CSV row)
- Missing optional fields
- Malformed recruiter records
- Invalid resume formatting / undetectable sections
- Validation failures
- Duplicate records
- Candidates with no derivable identifier (last-resort fallback ID)

Candidate failures shall be isolated and reported in
`failed_candidates.json` without terminating the overall batch.

------------------------------------------------------------------------

# 10. Acceptance Criteria

The project shall be considered complete when it can:

- Read recruiter CSV files matching the documented schema.
- Read resume TXT files from a directory.
- Process candidates in batches with per-candidate isolation.
- Match candidate records deterministically.
- Extract all required fields.
- Normalize all supported fields to documented canonical formats.
- Merge candidate information per the documented scalar/list rules.
- Track provenance for every retained value.
- Compute per-field and overall confidence per the documented table.
- Produce canonical candidate profiles.
- Generate configurable output via `config.json`.
- Validate output against the requested config shape.
- Export successful and failed candidates separately, plus a CLI
  summary line.
- Reproduce the worked example in `04_DATA_SCHEMAS_AND_EXAMPLES.md`
  exactly.

------------------------------------------------------------------------

# 11. Future Scope (Not Included)

Possible future enhancements include:

- Resume PDF support
- ATS JSON support
- GitHub integration
- LinkedIn integration
- Web dashboard
- REST API
- Database persistence
- Additional normalization rules
- OCR support
- Additional input sources
- General-purpose JSONPath config resolver