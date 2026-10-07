# ADR 0017: Connected review and revision-checked decisions

Status: accepted for v0.50.0

## Context

The API already stored decisions while the UI simulated a single example. Decision POSTs could silently supersede evidence another reviewer had just saved, and audit records committed after decisions in a separate transaction. Several other API routes lacked authentication or checked snapshot ownership after reading files. The first migration imported current model metadata, making a fresh database differ from an incremental upgrade.

## Decision

Connect the local identity desk to authenticated, organization-scoped APIs. Preserve the static Pages demo explicitly. Keep candidate and history queries bounded, search escaped, and workload aggregation in the database.

Require the candidate's observed revision for every decision. Advance it through one conditional update and append a decision with a unique candidate/revision pair. Commit the decision and sanitized audit event in one transaction. Order history by revision, independent of wall-clock ties. Return 409 for stale saves and require the desk to refresh before retrying.

Require explicit demo credentials, use the authenticated actor for quarantine attribution, and scope snapshots before reading files. Baseline profiles must describe the same organization and source object. Freeze the pre-0.50 baseline schema and backfill decision revisions in a separate migration.

## Consequences

Clients must supply `expected_revision` and explicit identity/scope headers. Quarantine clients must remove `reviewer_id`. Existing decision history is retained, with equal-time migration ties ordered by UUID. Reviews remain evidence and candidate states; applying decisions to canonical clusters or published outputs requires a separate designed workflow. Demo identities and SQLite verification remain reference behavior, with production identity and PostgreSQL runtime evidence required separately.
