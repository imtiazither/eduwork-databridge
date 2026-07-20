# Architecture

EduWork DataBridge uses a modular-monolith architecture for its first complete release. Packages have explicit interfaces but deploy as a manageable application stack.

## Central flow

Source data → immutable raw snapshot → contract/profile → versioned mapping → validation/quarantine → identity review → canonical records → traceable export.

Phases 0–14 implement the governed data path from immutable extraction through reviewable analytics, lineage-aware products, operations/security, evaluator documentation, benchmark and supply-chain evidence, and release-candidate controls. Target-environment hardening and partner pilots remain explicit future work.

## Phase 0–14 components

- FastAPI service with source, profile, mapping-preview, validation, quarantine, and deterministic-matching endpoints
- PostgreSQL-oriented SQLAlchemy control/canonical schema and four Alembic revisions
- Pydantic configuration/API contracts and JSON Schema 2020-12 exports
- Deterministic synthetic HRIS, LMS, assessment, credential, and identity-truth fixtures
- Safe CSV, XLSX, JSON, Parquet, REST, and PostgreSQL extraction with immutable raw evidence
- Polars profiles, approved baselines, schema/metric drift comparisons, and masked top-value evidence
- Bounded mapping DSL, governed lookups, deterministic outputs, masked row errors, diffs, and registered plugins
- Structural, completeness, validity, uniqueness, referential, temporal, cross-source, and timeliness validation with persisted results and quarantine history
- Trusted-ID and approved composite exact matching, conflict blocking, reversible decisions, and synthetic truth evaluation
- Probabilistic blocking, weighted comparison evidence, explicit synthetic parameter estimation, illustrative thresholds, gray-zone review, and persisted model/run attribution
- Run/field lineage, OpenLineage-compatible events, governed marts, masked CSV/Parquet exports, checksums, dictionaries, and retention
- Dagster definitions plus local asset dependencies, partitions, schedules, retries, watermarks, change hashes, incremental skip, backfills, run state, and OpenTelemetry-compatible telemetry
- Isolated demo identity, OIDC-ready claims conversion, organization/permission authorization, audit events, security middleware, export controls, and retention enforcement
- Strict MkDocs site, evaluator/developer paths, synthetic UI/lineage illustrations, and a synthetic walkthrough video
- Versioned benchmark, regression budgets, SBOMs, audits, package artifacts, release checksums, pinned CI, and Docker scan/sign/attestation workflow hooks
- React/TypeScript evaluator shell and Docker Compose developer topology

## Data zones

- Bronze: immutable, content-addressed raw snapshots and manifests (Phase 4)
- Silver preparation: mapping, validation, quarantine, and deterministic identity evidence (Phases 6–8); approved canonical publication remains later work
- Gold: documented training participation, credential status, and data-quality trend marts plus governed exports (Phase 10)
- Control plane: source, contract, processing, match-model, lineage, mart/export, orchestration, retention, audit, and access metadata (Phases 2–12)

## Tenancy

Organization-owned rows carry `organization_id`. Queries must be scoped through repository/service functions; the database schema also uses scoped uniqueness constraints. Production row-level security is a later deployment hardening option.

## Decisions

See `docs/architecture/decisions` for architecture decision records.
