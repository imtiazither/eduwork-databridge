# Developer Setup

## Prerequisites

- Python 3.12
- uv
- Node.js 24 LTS or another supported LTS
- Docker with Compose for the complete local stack

## Install

```bash
uv sync --frozen --extra dev
npm --prefix apps/reviewer-ui ci
```

## Generate and migrate

```bash
make generate
uv run alembic upgrade head
uv run python -m eduwork_databridge.seed
```

## Run

```bash
make api
make ui
```

## Verify

```bash
make check
make docs-build
make benchmark-smoke
make release-verify
```

## Working rules

- Add or update tests and documentation with behavior changes.
- Never add real personal or partner data to fixtures, issues, logs, screenshots, or videos.
- Regenerate JSON Schemas and the data dictionary when models change.
- Create an ADR for changes to public contracts, security boundaries, migrations, licensing, or maturity claims.
