# EduWork DataBridge

[![CI](https://github.com/imtiazither/eduwork-databridge/actions/workflows/ci.yml/badge.svg)](https://github.com/imtiazither/eduwork-databridge/actions/workflows/ci.yml)
[![GitHub Pages](https://github.com/imtiazither/eduwork-databridge/actions/workflows/pages.yml/badge.svg)](https://github.com/imtiazither/eduwork-databridge/actions/workflows/pages.yml)

[Explore the product site](https://imtiazither.github.io/eduwork-databridge/) · [Browse the documentation](https://imtiazither.github.io/eduwork-databridge/docs/)

One training report may need an employee roster from HR, completion records from an LMS, scores from an assessment file, and awards from a credential system. The joins usually happen in a spreadsheet. When an ID is missing or two accounts look alike, the reasoning can disappear inside the finished report.

EduWork DataBridge is an open-source reference implementation for making that reconciliation inspectable. It keeps source evidence, checks the awkward records, separates uncertain identity matches from safe ones, and carries lineage into governed outputs.

> The practical question: who completed the training, passed, and received the credential, and can we show where every part of that answer came from?

Read [the story behind the project and its contribution](docs/PROJECT_STORY.md), the [plain-English explainer](EduWork_DataBridge_Explanation_ELI5.pdf), or the shorter [five-page field guide](docs/EduWork_DataBridge_Field_Guide.pdf).


## What it helps you do

- Safely ingest and preserve evidence from fragmented learning and workforce systems
- Profile, map, validate, quarantine, and review data before it reaches analytics products
- Resolve identity candidates transparently, with conflict blocking and human-review boundaries
- Publish documented, masked, lineage-aware marts and exports for approved internal uses
- Start a bounded private partner workflow while keeping real data, credentials, proprietary mappings, and results outside this public repository

## See the synthetic case file

The reviewer desk uses a deterministic public fixture: 120 fictional people, 366 learning events, 120 assessment results, 25 credential awards, and 43 planted problem occurrences.

![EduWork DataBridge reviewer desk showing the five-stop evidence path](docs/assets/reviewer-desk.jpg)

The desk includes a source inventory, filterable exception types, an identity-review preview, and a field-lineage view. Its review decision is deliberately non-persistent; the backend services remain the authoritative path for recorded decisions.

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

Run the API in another terminal first. The Vite development server proxies `/api` to `http://127.0.0.1:8000`, so the reviewer desk works with the documented `make api` and `make ui` commands without extra environment setup.

The GitHub Pages build uses `npm run build:pages`. It publishes an explicitly labeled static synthetic demo at the repository subpath and bundles the MkDocs site under `/docs/`; it does not imply that the FastAPI service is hosted by GitHub Pages.

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
