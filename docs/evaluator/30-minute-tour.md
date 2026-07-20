# 30-Minute Evaluator Tour

This path uses synthetic data only and is intended to answer: **Can I run it, understand it, and verify the central claims without the author present?**

## Minutes 0–5: orient

1. Read the project statement and maturity warning in `README.md`.
2. Open `ARCHITECTURE.md` and the phase diagrams.
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

## Minutes 15–22: complete technical flow

```bash
uv run python scripts/run_phase8_demo.py
```

Then inspect:

- `var/raw` for immutable content-addressed source evidence
- `var/mapped` for derived mapped output
- database tables for profiles, validation, quarantine, and matching evidence

## Minutes 22–27: quality and security

```bash
make check
uv run python scripts/run_benchmark.py --preset small --output benchmark-results/current.json
uv run python scripts/verify_release.py
```

## Minutes 27–30: decide

Ask:

- Are inputs, rules, outputs, limitations, and evidence traceable?
- Are synthetic results clearly distinguished from company outcomes?
- Can one bounded company workflow be configured without changing the core?
- Are remaining deployment checks explicit?
