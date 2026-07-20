# EduWork DataBridge

[![CI](https://github.com/imtiazither/eduwork-databridge/actions/workflows/ci.yml/badge.svg)](https://github.com/imtiazither/eduwork-databridge/actions/workflows/ci.yml)

EduWork DataBridge is an industry-neutral, open-source reference framework for turning fragmented learning, training, skills, credential, and workforce records into documented, validated, traceable, analytics-ready data.

## Current maturity

This repository implements Blueprint **Phases 0–14**:

- Phases 0–12: governed ingestion, profiling/drift, bounded mapping, validation/quarantine, deterministic and probabilistic identity review, lineage, marts/exports, orchestration/telemetry, identity, authorization, audit, and retention.
- Phase 13: strict MkDocs documentation site, 30-minute evaluator path, developer path, architecture/configuration/API/security/deployment guides, troubleshooting/FAQ, synthetic screenshots, and a 36-second synthetic walkthrough video.
- Phase 14: versioned reference benchmark and regression budgets, dependency audits, targeted secret scan, Python/frontend SBOMs, Python wheel/source distributions, release checksums, pinned CI actions, container scan/sign/attestation workflow hooks, and external-review/release/risk/claims checklists.

The implementation blueprint is complete. The release remains a **pre-production release candidate** until target-environment Docker/PostgreSQL/OIDC/signing checks and a real bounded partner pilot are completed.

## What it helps you do

- Safely ingest and preserve evidence from fragmented learning and workforce systems
- Profile, map, validate, quarantine, and review data before it reaches analytics products
- Resolve identity candidates transparently, with conflict blocking and human-review boundaries
- Publish documented, masked, lineage-aware marts and exports for approved internal uses
- Start a bounded private partner workflow while keeping real data, credentials, proprietary mappings, and results outside this public repository

## Why use it

EduWork DataBridge makes transformations and governance inspectable: source snapshots, contracts, mappings, validation results, matching evidence, lineage, exports, audit events, benchmarks, SBOMs, tests, and release checks are all part of the implementation. It reduces the risk of treating one-off data work as a black box and gives technical evaluators a reproducible place to start.

Read the complete [project overview, usage guide, and benefits](docs/PROJECT_OVERVIEW.md).

## Who can use the framework

- EdTech and learning-platform vendors
- Professional and customer-training providers
- Corporate learning and development teams
- Organizations consolidating HRIS, LMS, CRM, assessment, and credential records
- Colleges and workforce programs through optional domain adapters

## Architecture

The first deployment path is a modular monolith:

- Python 3.12+
- FastAPI
- SQLAlchemy 2 and Alembic
- PostgreSQL
- Pydantic v2 and JSON Schema
- React + TypeScript + Vite
- Docker Compose

See [ARCHITECTURE.md](ARCHITECTURE.md) and [the context diagram](docs/architecture/context.mmd).

## Quickstart

### Prerequisites

- Python 3.12
- uv
- Node.js 24 LTS or a currently supported LTS release
- Docker with Compose support for the full local stack

### Backend

```bash
uv sync --frozen --extra dev
uv run python scripts/generate_synthetic_data.py --preset small --seed 20260719
uv run alembic upgrade head
uv run python -m eduwork_databridge.seed
uv run python scripts/run_phase8_demo.py
uv run uvicorn eduwork_databridge.main:app --reload
```

The public API surface includes source processing, matching, marts, exports, lineage, orchestration, identity, audit, and retention operations:

- `POST /api/v1/sources/{source_id}/test`
- `GET /api/v1/sources/{source_id}/objects/{object_key}/discover`
- `POST /api/v1/sources/{source_id}/extract` with `X-Organization-ID`
- `POST /api/v1/profiles`
- `POST /api/v1/mappings/preview`
- `POST /api/v1/validations`
- `POST /api/v1/quarantine/{quarantine_id}/resolve`
- `POST /api/v1/matches/deterministic/synthetic`
- `POST /api/v1/matches/probabilistic/synthetic`
- `POST /api/v1/marts`
- `POST /api/v1/exports`
- `GET /api/v1/lineage/{node_id}`
- `POST /api/v1/orchestration/runs`
- `POST /api/v1/retention/apply`
- `GET /api/v1/me`
- `GET /api/v1/audit`

Use `X-Demo-User: demo-admin` only in non-production demo mode. Production deployments must replace it with verified OIDC claims.

### Frontend

```bash
cd apps/reviewer-ui
npm ci
npm run dev
```

### Tests and generated artifacts

```bash
make check
make generate
make docs-build
make benchmark-smoke
make release-verify
```

### Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

The demo configuration is under `configs/demo`. It contains no real people or company data.

## Repository map

- `packages/eduwork_databridge`: backend, models, connectors, profiling/mapping/validation, deterministic and probabilistic matching, lineage, marts/exports, orchestration/telemetry, identity/authorization, audit, and retention
- `apps/reviewer-ui`: typed frontend shell for later review workflows
- `data/synthetic`: deterministic small and medium public fixtures plus identity truth sets
- `migrations`: Alembic database migrations
- `schemas`: committed JSON Schemas generated from Pydantic models
- `configs/demo`: validated source, mapping, validation, and pipeline examples
- `docs`: evaluator/developer paths, architecture, guides, release checklists, screenshots, and walkthrough video
- `benchmark-baseline`: versioned environment/results and regression budgets
- `release`: SBOMs, audits, package artifacts, environment gaps, verification, and checksums
- `.github`: pinned CI, dependency updates, templates, and tag-triggered release workflow

## Public/private boundary

Public assets use synthetic data and generic configuration. Never commit partner data, identifiers, credentials, endpoints, proprietary mappings, unapproved screenshots, or pilot results.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
