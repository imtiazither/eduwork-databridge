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

Use separate terminals for the two commands, then open `http://127.0.0.1:5173`. The Vite server proxies local `/api` requests to `http://127.0.0.1:8000`.

To point the UI at another API, create `apps/reviewer-ui/.env.local` with `VITE_API_BASE_URL=<approved-origin>`. The API permits the origins configured by `EDUWORK_ALLOWED_ORIGINS`; review that list before exposing a non-local environment.

## Verify

```bash
make check
make docs-build
make benchmark-smoke
make release-verify
```

## Build the GitHub Pages artifact

```bash
npm --prefix apps/reviewer-ui run build:pages
uv run mkdocs build --strict --site-dir apps/reviewer-ui/dist/docs
cp apps/reviewer-ui/dist/index.html apps/reviewer-ui/dist/404.html
touch apps/reviewer-ui/dist/.nojekyll
```

The Pages build is a static synthetic case file. It deliberately skips API requests and labels itself as a demo. The normal development and deployment builds keep the live API integration.

## Working rules

- Add or update tests and documentation with behavior changes.
- Never add real personal or partner data to fixtures, issues, logs, screenshots, or videos.
- Regenerate JSON Schemas and the data dictionary when models change.
- Create an ADR for changes to public contracts, security boundaries, migrations, licensing, or maturity claims.
