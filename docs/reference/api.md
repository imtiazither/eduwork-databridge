# API Reference

- `GET /healthz` — process liveness
- `GET /readyz` — database readiness
- `GET /api/v1/version` — current product version
- `GET /api/v1/demo/summary` — counts and planted defect evidence from the small public synthetic fixture
- `GET /api/v1/organizations` — authenticated inventory limited to actor organization memberships
- `GET /api/v1/sources` — authenticated organization-scoped inventory; requires `sources:read` and `X-Organization-ID`
- `POST /api/v1/sources/{source_id}/test` — authenticated, organization-scoped connection check
- `GET /api/v1/sources/{source_id}/objects/{object_key}/discover` — authenticated, organization-scoped schema discovery with no raw samples returned
- `POST /api/v1/sources/{source_id}/extract` — immutable extraction; requires `X-Organization-ID` and an object key body
- `POST /api/v1/profiles` — requires `profiles:write`; scoped snapshot and same-source baseline checks before comparison, with audit attribution
- `POST /api/v1/mappings/preview` — bounded mapping dry run with masked row errors
- `POST /api/v1/validations` — multi-category validation, quality dimensions, persisted results, and quarantine IDs; optional `mapping_id` and `lookup_ids` validate the mapped canonical records instead of the raw snapshot, and the response labels its `record_source`
- `POST /api/v1/quarantine/{quarantine_id}/resolve` — requires `validation:write`; authenticated actor attribution and audit, with a status and non-blank note
- `POST /api/v1/matches/deterministic/synthetic` — organization-scoped deterministic linkage and synthetic truth evaluation
- `GET /api/v1/matches/review-queue` — permission-gated candidate queue with status, `needs_review`, `unreviewed`, and escaped record-key `q` search, plus bounded pagination
- `GET /api/v1/matches/review-queue/summary` — organization-scoped workload totals, unreviewed count, and current status counts
- `POST /api/v1/matches/{candidate_id}/decisions` — permission-gated reasoned match, no-match, defer, or escalation decision
- `GET /api/v1/matches/{candidate_id}/decisions` — organization-scoped decision history, highest revision first, with bounded `limit` and `offset`
- `POST /api/v1/matches/probabilistic/synthetic` — explicit synthetic estimation, probabilities, gray-zone candidates, and model/run evidence
- `POST /api/v1/marts` — permission-gated governed mart build; optional `source_snapshot_id` and `mapping_id` register lineage back to the raw snapshot
- `POST /api/v1/exports` — permission-gated documented masked export with automatic mart-to-export lineage
- `GET /api/v1/lineage/{node_id}` — organization-scoped lineage trace; accepts a lineage node id or a snapshot, mart, or export identifier
- `POST /api/v1/orchestration/runs` — permission-gated asset run with partition and watermark
- `POST /api/v1/retention/apply` — dry-run-by-default retention enforcement
- `GET /api/v1/me` — current demo/OIDC-adapted actor
- `GET /api/v1/audit` — permission-gated organization audit events covering extraction, mapping previews, validation, matching, marts, exports, orchestration, and retention

## Authentication and organization scope

Health, readiness, version, and the public synthetic summary remain available without authentication. Other data and workflow routes require an actor. Local demo clients must explicitly send `X-Demo-User: demo-admin` or `demo-viewer`; missing or invalid identity returns 401. Production infrastructure must provide verified identity rather than enabling the demo provider.

Organization-scoped routes require `X-Organization-ID` and actor membership. Source connection/discovery also require a registered active source in that organization and `sources:read`. Snapshot processing checks ownership before reading files. Quarantine resolution derives the reviewer from the actor and rejects caller-supplied `reviewer_id` fields.

## Match review

The queue and summary require `matching:write`. Queue `limit` defaults to 50 and accepts 1–200; `offset` starts at zero. Status accepts `pending`, `auto_match`, `review`, `trusted_id_conflict`, `match`, `no_match`, `defer`, or `escalate`. `q` searches either record key case-insensitively with a maximum of 100 characters; percent and underscore are literal characters. Filters combine when supplied together.

`needs_review=true` includes pending, review, conflict, deferred, and escalated candidates. `unreviewed=true` means no human decision exists, including automatic suggestions. Summary returns `total_candidates`, `unreviewed_candidates`, `needs_review_candidates`, and `by_status`.

Queue rows include `revision`, evidence, `decision_count`, and `latest_decision`. Submit the observed revision with a non-blank reason:

```json
{
  "decision": "defer",
  "reason": "Source owner must confirm the duplicate account.",
  "expected_revision": 0
}
```

Decision choices are `match`, `no_match`, `defer`, and `escalate`. A successful save returns the next `revision`, preserves the prior decision through `supersedes_decision_id`, and commits the `matching.decision.recorded` audit event in the same transaction. A stale revision returns 409 with code `decision_conflict`. Refresh before submitting another decision; omitting the revision returns 422.

History defaults to 50 rows, accepts `limit` 1–200 and non-negative `offset`, and sorts by descending revision. Reasons and reviewers remain in append-only history. Audit details record candidate, decision, revision, and supersession identifiers without duplicating the reason.

Saving a review changes candidate status and evidence; it does not rewrite source records, clusters, marts, or exports. See the [review workbench guide](../guides/review-workbench.md).
