# EduWork DataBridge: Project Overview, Usage Guide, and Benefits

**Version:** 0.15.0  
**Status:** Blueprint-complete, pre-production reference implementation  
**License:** Apache-2.0

For the human problem that motivated the reference design, read [the project story](PROJECT_STORY.md). The [five-page field guide](EduWork_DataBridge_Field_Guide.pdf) pairs that story with the current reviewer desk.

## What it is

EduWork DataBridge is an open-source interoperability and data-governance foundation for organizations that need to work across fragmented learning, training, skills, credential, HRIS, LMS, CRM, assessment, and workforce records.

It is designed to turn source-system extracts into documented, validated, reviewable, traceable, and exportable data products. It does this without assuming that one source system is the permanent source of truth and without treating a person's email address as a universal identity.

The project is intentionally a **reference implementation**, not a finished institutional deployment. Its public fixtures, screenshots, benchmark, probability thresholds, and walkthrough are synthetic. It does not claim customer adoption, regulatory certification, production readiness for every environment, or measured business outcomes.

## What it can be used for

Typical uses include:

- Combining data from HRIS, LMS, CRM, assessment, credential, learning-platform, and workforce systems
- Preparing a governed analytics foundation for learning, training, credential, skills, or workforce operations
- Evaluating source-data quality before analytics or migration work begins
- Creating a reviewable pathway for resolving duplicate or conflicting person identities
- Producing documented training, credential-status, and data-quality marts for approved internal uses
- Demonstrating how to preserve lineage from raw source data through rules, validation, matching, marts, and exports
- Starting a bounded partner pilot without placing real partner records in the public repository

## Core capabilities

### Safe ingestion and evidence preservation

- Read-only CSV, XLSX, JSON, Parquet, REST, and PostgreSQL connectors
- File, archive, network, request-size, page-count, and retry controls
- Immutable content-addressed raw snapshots, checksums, source manifests, cursors, and resume metadata

### Quality, mapping, and validation

- Masked profiling and approved profile baselines
- Drift comparisons that make schema and quality changes visible
- A bounded, versioned mapping DSL and governed lookup tables
- Structural, completeness, validity, uniqueness, referential, temporal, cross-source, and timeliness validation
- Quarantine, resolution, and reprocessing history for records that need attention

### Identity review

- Organization-scoped deterministic matching using trusted identifiers and approved composite keys
- Trusted-ID conflict blocking and reversible decisions
- Probabilistic candidate blocking and comparison evidence for a synthetic demonstration fixture
- Explicit auto-match, review, no-match, and conflict states
- Gray-zone review evidence and model/run attribution

### Governed products and operations

- Run and field lineage plus OpenLineage-compatible event output
- Documented training participation, credential status, and data-quality trend marts
- Permission-gated, masked CSV and Parquet exports with checksums, dictionaries, lineage, and retention metadata
- Asset dependencies, partitions, schedules, retries, watermarks, change hashes, incremental skips, backfills, and sanitized telemetry
- Demo/OIDC-ready identity contracts, organization and permission authorization, audit events, security headers, rate limits, export controls, and retention enforcement

## Benefits of using it

1. **More reliable cross-system data.** The platform preserves source evidence, exposes data quality problems, and makes transformations explicit rather than relying on opaque spreadsheets or one-off scripts.
2. **Traceability.** Reviewers can trace a published field or export back to source snapshots, mappings, validation rules, lineage records, and versions.
3. **Safer identity handling.** It blocks known trusted-ID conflicts and separates automatic, review, no-match, and conflict outcomes instead of silently merging records.
4. **Governance by design.** Organization scope, permissions, masking, audit records, checksums, and retention controls are part of the implementation rather than afterthoughts.
5. **Faster evaluation and extension.** Synthetic fixtures, a 30-minute evaluator tour, developer instructions, JSON Schemas, docs, tests, and reproducible evidence make the project inspectable and extendable.
6. **Lower pilot risk.** A real organization can begin with one authorized, bounded workflow while keeping proprietary data, credentials, mappings, endpoints, and results private.

## How to use it

### 1. Run the reference implementation locally

Prerequisites:

- Python 3.12
- uv
- Node.js 24 LTS or another supported LTS version
- Docker with Compose for the complete local stack

```bash
uv sync --frozen --extra dev
npm --prefix apps/reviewer-ui ci
make generate
uv run alembic upgrade head
uv run python -m eduwork_databridge.seed
make check
```

Start the API and the reviewer UI:

```bash
make api
make ui
```

For the full local topology:

```bash
cp .env.example .env
docker compose up --build
```

### 2. Take the evaluator path

Use `docs/evaluator/30-minute-tour.md` to inspect the synthetic data, run the core flow, validate generated artifacts, and understand the evidence boundary without needing author assistance.

### 3. Extend it for an approved workflow

1. Define a small, authorized use case and a data owner.
2. Keep partner source data, credentials, URLs, proprietary mappings, and results in a private companion repository or environment.
3. Add a strict source contract and synthetic fixture.
4. Profile source data and define versioned mappings and validation rules.
5. Review identity matching rules, thresholds, and human-review capacity before using real records.
6. Produce only documented marts and permission-gated exports.
7. Add tests, lineage, audit, documentation, and deployment evidence with each extension.

## Verification and release evidence

The v0.15.0 release includes:

- 70 Python tests with 89.78% measured coverage
- Ruff, format, and strict mypy checks across 81 Python source and script files
- Four frontend Vitest tests and a TypeScript/Vite production build
- Eleven generated JSON Schemas and four Alembic migrations
- A strict MkDocs documentation build
- A versioned synthetic benchmark with regression budgets
- Python CycloneDX plus frontend CycloneDX and SPDX SBOMs
- Dependency audits reporting zero known vulnerabilities at the time of verification
- A targeted secret scan reporting zero findings
- Built and inspected Python wheel and source-distribution artifacts
- SQLite reference backup/restore verification
- SHA-256 checksums, a release manifest, a 36-second synthetic walkthrough video, and a final completion report

## Important limits and responsible-use boundary

- Synthetic benchmark times and matching thresholds are not production service-level objectives or calibrated production guarantees.
- The code does not make consequential decisions about employment, eligibility, admissions, discipline, disability, or services.
- Public materials contain synthetic data only.
- A real deployment still needs target-environment validation for Docker/Compose, PostgreSQL, OIDC, image scanning, signing, attestation, backup/restore, access review, retention, privacy, and compliance requirements.
- A bounded partner pilot is the next evidence step; do not infer company adoption, cost savings, learning outcomes, or regulatory compliance from this repository.

## Where to find more information

- `README.md` — quick start and repository map
- `docs/evaluator/30-minute-tour.md` — evaluator guide
- `docs/developer/getting-started.md` — developer setup
- `docs/concepts/architecture.md` — architecture and data zones
- `docs/release/claim-boundaries.md` — supported and unsupported claims
- `docs/release/release-candidate-checklist.md` — final release checks
- `docs/release/docker-validation.md` — target-environment deployment validation
