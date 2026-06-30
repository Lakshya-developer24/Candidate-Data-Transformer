# System Architecture

## Project

**Project:** Multi Source Candidate Data Transformer

**Architecture Style:** Modular Data Processing Pipeline

**Status:** Frozen v1 — ready for implementation

------------------------------------------------------------------------

# 1. Architectural Overview

The application is designed as a deterministic pipeline. Each stage has
a single responsibility and communicates only with the next stage. Every
candidate is processed independently, allowing batch execution without
shared state.

    CSV Rows + Resume Files
            |
            v
    Candidate Matcher
            |
            v
    Reader
            |
            v
    Extractor
            |
            v
    Normalization
            |
            v
    Merge
            |
            v
    Canonical Candidate
            |
            v
    Projection
            |
            v
    Validation
            |
            v
    profiles.json / failed_candidates.json

------------------------------------------------------------------------

# 2. Design Principles

- Single Responsibility Principle
- Separation of Concerns
- Deterministic Processing
- Canonical Internal Representation
- Batch Failure Isolation
- Configuration Driven Output
- Extensible Pipeline (matcher, readers, and extractors are all
  swappable behind stable interfaces)

------------------------------------------------------------------------

# 3. Candidate Matcher

Implemented behind a `CandidateMatcher` interface so the matching
strategy is swappable without touching the rest of the pipeline.

**Default implementation:** match a CSV row to a resume file by
normalized primary email. This is an internal matching key, not a
filename contract — resume filenames are not assumed to encode email.

Responsibilities:

- Match recruiter records with resumes.
- Handle unmatched records on both sides.
- Produce independent candidate work items for the batch engine.

Does not:

- Read file contents.
- Extract fields.
- Merge data.

Outcomes:

- **Matched pair** → one candidate work item with both sources.
- **Unmatched CSV row** → CSV-only candidate work item.
- **Unmatched resume file** → resume-only candidate work item; its
  email is pulled from resume text during extraction, for use in
  `candidate_id` derivation.

------------------------------------------------------------------------

# 4. Reader

Responsibilities:

- Read CSV rows (via `csv.DictReader`, keyed on the documented header
  row).
- Read resume text files as raw UTF-8 strings.
- Return raw content only.

Does not:

- Parse business information.
- Normalize values.

------------------------------------------------------------------------

# 5. Extractor

Responsibilities:

- Convert raw content into `CandidateValue` objects.
- Extract: Name, Email, Phone, Headline, Skills, Experience, Education.
- Assign confidence, source, and method **at this point** — these are
  never assigned or modified later in the pipeline.

## CSV Extraction

Each populated CSV column maps directly to a `CandidateValue` with
`source = "recruiter_csv"`, `method = "csv_direct"`.

## Resume Extraction

Entirely rule-based, in two steps:

1. **Section-header detection** — raw resume text is split into named
   sections using regex matching against the recognized header strings
   (full list in `04_DATA_SCHEMAS_AND_EXAMPLES.md`).
2. **In-section extraction** — regex and keyword matching are applied
   within each detected section to produce `CandidateValue` objects,
   with `method` set to `resume_regex`, `resume_keyword`, or
   `resume_inferred` depending on the technique used (see Confidence
   Table below).

No NLP libraries or LLMs are used at any point.

------------------------------------------------------------------------

# 6. Normalization

Responsibilities — transforms `CandidateValue.value` only:

| Field  | Canonical format                          |
|--------|--------------------------------------------|
| emails | lowercased                                  |
| phones | E.164                                       |
| dates  | `YYYY-MM`                                   |
| skills | canonical name via in-code alias dictionary |

It never:

- Changes confidence.
- Changes source or method.
- Resolves conflicts between values.

Conflict resolution is exclusively Merge's responsibility.

------------------------------------------------------------------------

# 7. Merge

Responsibility: combine structured and unstructured data into one
canonical candidate.

## Scalar Fields

Examples: `full_name`, `headline`, `years_experience`, an individual
email, an individual phone.

Rules:

1. Higher `CandidateValue.confidence` wins.
2. If two sources produce equal normalized values, the result becomes
   **"agreed"**: `confidence = min(1.0, higher_of_two + 0.05)`,
   `source` records both sources, `method = "agreed"`.
3. On an exact confidence tie between conflicting (non-equal) values,
   prefer the `csv_direct` value.
4. The losing value is dropped entirely — it is not retained anywhere
   on the canonical candidate.

## List Fields

List fields use **dedupe-key union**, not winner-take-all:

| Field      | Dedupe key                                          |
|------------|-------------------------------------------------------|
| skills     | canonical skill name                                  |
| experience | normalized(company) + normalized(title)               |
| education  | normalized(institution) + normalized(degree)           |

Once two entries share a dedupe key, each field *inside* that entry
(e.g. `start`, `end`, `summary`) is resolved independently using the
same scalar `CandidateValue` rule above (confidence wins, equal →
agreed, tie → CSV).

**Concrete example:** the CSV's `current_company` / `current_title`
columns produce one experience entry with `start = null`, `end = null`.
If the resume contains a matching `company + title`, the two entries
merge field-by-field: the resume's `start`/`end` dates are adopted (the
CSV entry has none to conflict with), while `company`/`title` go
through the standard scalar agreement rule. This is the canonical
worked example for merge behavior — see
`04_DATA_SCHEMAS_AND_EXAMPLES.md` for the literal input/output.

------------------------------------------------------------------------

# 8. Confidence Table

Assigned at extraction time, fixed per method:

| Method            | Confidence |
|-------------------|------------|
| `csv_direct`      | 0.95       |
| `resume_regex`     | 0.80       |
| `resume_keyword`   | 0.80       |
| `resume_inferred`  | 0.60       |
| `agreed` bonus     | `min(1.0, higher_of_two + 0.05)` |

`overall_confidence` (on the `Candidate`, computed last, after Merge)
= mean of all non-null final field confidences, rounded to 2 decimals.

------------------------------------------------------------------------

# 9. Candidate ID

```
candidate_id = "cand_" + sha256(normalized_primary_email)[:12]
```

Fallback order if no email is available anywhere for the candidate:

1. `sha256(normalized_full_name + first_normalized_phone)[:12]`
2. `sha256(source_filename + row_index)[:12]` (last resort, guarantees
   a deterministic ID even with no identifying contact info)

------------------------------------------------------------------------

# 10. Canonical Candidate

All downstream stages operate exclusively on one internal `Candidate`
object. Every supported input source must eventually produce this same
representation.

------------------------------------------------------------------------

# 11. Projection

Responsibilities:

- Select fields per `config.json`.
- Rename fields (`"from"` remap).
- Apply a per-field normalization override, if configured.
- Toggle provenance (source/method) on or off.
- Toggle confidence on or off.
- Handle missing values per `on_missing`: `null` / `omit` / `error`
  (the `"error"` case is enforced by Validation, not Projection).

The projection layer implements a **minimal path resolver**, not a
general JSONPath engine. It supports only the specific path shapes used
in the documented config examples:

- `emails[0]` — index into a list field
- `skills[].name` — map a sub-field across all entries of a list field
- `experience[].company` — same, for nested object lists

Any path shape outside these is unsupported by design.

Projection operates on a copy/view of the canonical `Candidate`. The
canonical record itself is **never mutated**.

------------------------------------------------------------------------

# 12. Validation

Responsibilities:

- Validate projected output, after Projection.
- Verify required fields are present.
- Verify output types match the projected schema.
- Enforce `on_missing = "error"`: if a required field is still absent
  after projection, validation raises **for that candidate only**.

Validation failures are isolated — they affect only the current
candidate and route it to `failed_candidates.json`.

------------------------------------------------------------------------

# 13. Internal Models

## CandidateValue

Stores one logical value together with its metadata.

Fields:

- `value`
- `confidence`
- `source` (e.g. `"recruiter_csv"`, `"resume_txt"`, or both for
  `"agreed"`)
- `method` (e.g. `"csv_direct"`, `"resume_regex"`, `"resume_keyword"`,
  `"resume_inferred"`, `"agreed"`)

Every extracted value is represented as a `CandidateValue`.

------------------------------------------------------------------------

## Candidate

Represents one canonical candidate.

Contains:

- `candidate_id`
- `full_name` → CandidateValue
- `emails` → list[CandidateValue]
- `phones` → list[CandidateValue]
- `location` → CandidateValue
- `links` → CandidateValue
- `headline` → CandidateValue
- `years_experience` → CandidateValue
- `skills` → list[CandidateValue]
- `experience` → list[CandidateValue]
- `education` → list[CandidateValue]
- `overall_confidence` (plain number, computed last)

This object remains stable regardless of input source.

Full field-level JSON shape: `04_DATA_SCHEMAS_AND_EXAMPLES.md`.

------------------------------------------------------------------------

# 14. Data Flow

    CSV Row
              \
               \
                ---> Candidate Matcher
               /
    Resume TXT
            |
            v
    Reader
            |
            v
    Extractor
            |
            v
    Normalization
            |
            v
    Merge
            |
            v
    Candidate
            |
            v
    Projection
            |
            v
    Validation
            |
            v
    JSON Output

------------------------------------------------------------------------

# 15. Batch Processing

The CSV contains multiple candidates while resumes exist as individual
text files. The batch engine:

1. Runs the Candidate Matcher to produce the union of matched pairs,
   CSV-only candidates, and resume-only candidates.
2. Loops over each candidate, running the full pipeline
   (Reader → Extractor → Normalization → Merge → Projection →
   Validation) independently.
3. Isolates failures per candidate — one failure does not stop or
   affect any other candidate's processing.
4. Collects successes into `output/profiles.json` and failures (with
   identifier and failure reason) into `output/failed_candidates.json`.
5. Prints a final CLI summary: total processed, succeeded, failed.

------------------------------------------------------------------------

# 16. Error Handling

Errors are isolated per candidate. Possible failures:

- Missing resume
- Invalid CSV row
- Invalid configuration
- Extraction failure
- No derivable `candidate_id` even after fallbacks (should not occur
  given the last-resort fallback, but handled defensively)
- Validation failure

Successful candidates continue processing regardless of failures
elsewhere.

------------------------------------------------------------------------

# 17. Scalability

The architecture is designed for recruiter exports containing thousands
of candidates.

Scalability comes from:

- Independent candidate processing.
- Stateless pipeline stages.
- No shared mutable state.
- Linear processing of candidate batches.

------------------------------------------------------------------------

# 18. Extensibility

New sources can be added by implementing:

- A new Reader.
- A new Extractor.
- Optionally, a new `CandidateMatcher` if matching logic must change.

The remaining pipeline remains unchanged because all processing occurs
on the canonical `Candidate` model.

------------------------------------------------------------------------

# 19. Architecture Summary

The architecture separates matching, reading, extraction,
normalization, merging, projection, and validation into independent
modules. `CandidateValue` carries metadata with every extracted value,
assigned once at extraction time per a fixed confidence table, and
never altered afterward except through documented merge rules. The
canonical `Candidate` model provides a stable internal representation,
enabling deterministic processing, modular implementation, graceful
batch failure handling, and straightforward future extension without
modifying the core pipeline.