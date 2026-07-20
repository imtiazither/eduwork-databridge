# Profiling and Drift Guide

Phase 5 uses Polars to profile row/sample counts, observed types, null and blank counts, distinctness, numeric summaries, string lengths, and top-value shares. Top values are SHA-256 fingerprints by default; raw examples are not persisted.

Profiles are stored by raw snapshot and may reference an approved baseline. Comparisons report added/removed fields, type changes, raw metric deltas, configurable threshold breaches, and baseline/current row counts.

Status meanings:

- stable: no configured threshold or schema change
- warning: additive schema change only
- drift: removed field, type change, or metric threshold breach

Drift is evidence for review, not a universal declaration that data is unusable. Thresholds in `configs/demo/profiles/default_v1.yml` are demonstration defaults and must be approved for each real workflow.
