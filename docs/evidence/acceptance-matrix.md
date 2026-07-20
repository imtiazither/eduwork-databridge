# Phase 0–2 Acceptance Matrix

## Phase 0

- Charter, scope, ADRs, evidence log, measures, and claim boundaries exist.
- The demo can be explained without implying later features are complete.

## Phase 1

- Backend and frontend install from lockfiles.
- Lint, static typing, tests, and frontend build pass.
- Compose configuration defines API, worker, UI, and PostgreSQL.
- Governance and security files exist.

## Phase 2

- Migration upgrades an empty database and downgrades cleanly.
- Canonical and control-plane models create without mapping errors.
- Organization-scoped repositories exclude other organizations.
- Pydantic models reject invalid extra configuration.
- Committed JSON Schemas equal generated output.
- Data dictionary equals model metadata.
- Seed metadata loads idempotently.
