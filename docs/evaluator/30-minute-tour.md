# 30-Minute Evaluator Tour

This path uses synthetic data only and is intended to answer: **Can I run it, understand it, and verify the central claims without the author present?**

## Minutes 0–5: start with the case

1. Read `docs/PROJECT_STORY.md` and the maturity warning in `README.md`.
2. Note the working question: who completed the training, passed, and received the credential?
3. Review `docs/evidence/release-manifest.json`.

## Minutes 5–10: install and verify

```bash
uv sync --frozen --extra dev
npm --prefix apps/reviewer-ui ci
make generate-check
```

## Minutes 10–15: database and synthetic evidence

```bash
uv run alembic upgrade head
uv run python -m eduwork_databridge.seed
uv run python scripts/verify_synthetic_data.py
```

Inspect `data/synthetic/small/dataset_manifest.json`: every file is fictional, checksummed, and accompanied by expected defect counts.

## Minutes 15–20: use the reviewer desk

In separate terminals:

```bash
make api
make ui
```

Open `http://127.0.0.1:5173` and inspect the source checks, exception desk, identity-review preview, and evidence trail. The preview decision is local UI state; it does not write a review decision to the database.

## Minutes 20–25: complete technical flow

```bash
uv run python scripts/run_phase8_demo.py
```

Then inspect:

- `var/raw` for immutable content-addressed source evidence
- `var/mapped` for derived mapped output
- database tables for profiles, validation, quarantine, and matching evidence

## Minutes 25–28: quality and security

```bash
make check
uv run python scripts/run_benchmark.py --preset small --output benchmark-results/current.json
uv run python scripts/verify_release.py
```

## Minutes 28–30: decide

Ask:

- Are inputs, rules, outputs, limitations, and evidence traceable?
- Are synthetic results clearly distinguished from company outcomes?
- Can one bounded company workflow be configured without changing the core?
- Are remaining deployment checks explicit?
