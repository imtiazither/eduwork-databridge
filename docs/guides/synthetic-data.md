# Synthetic Data Guide

Phase 3 provides deterministic HRIS, LMS, assessment, credential, and identity-truth fixtures. Every record is fictional and uses the reserved `example.test` domain.

## Generate

```bash
uv run python scripts/generate_synthetic_data.py --preset small --seed 20260719
uv run python scripts/generate_synthetic_data.py --preset medium --seed 20260719
uv run python scripts/generate_synthetic_data.py --preset benchmark --seed 20260719
```

Small and medium fixtures are committed for evaluation. The benchmark preset is generated on demand to avoid repository bloat.

## Presets

- small: 120 people, 6 courses, 3 expected participations per person
- medium: 2,000 people, 18 courses, 6 expected participations per person
- benchmark: 100,000 people, 80 courses, 10 expected participations per person

## Controlled defects

The manifest records expected counts for missing employee IDs, name variants, duplicate LMS accounts, conflicting departments, invalid completion statuses, completion-before-assignment errors, credential-before-assessment errors, late events, and formula-like text.

## Truth data

`truth/identity_truth.json` links fictional source identifiers to a fictional canonical person UUID. It is test-only evaluation evidence for future entity-resolution phases. It must never be treated as a company result.

## Reproducibility

The same preset and seed produce the same file checksums, including the XLSX and Parquet files. Verify committed fixtures with:

```bash
uv run python scripts/verify_synthetic_data.py
```
