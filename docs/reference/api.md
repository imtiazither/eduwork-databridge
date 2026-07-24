# Phase 12 API

- `GET /healthz` — process liveness
- `GET /readyz` — database readiness
- `GET /api/v1/version` — product maturity and completed phases
- `GET /api/v1/demo/summary` — counts and planted defect evidence from the small public synthetic fixture
- `GET /api/v1/organizations` — seeded metadata
- `GET /api/v1/sources` — explicitly organization-scoped source inventory; requires `X-Organization-ID`
- `POST /api/v1/sources/{source_id}/test` — safe connection/configuration check
- `GET /api/v1/sources/{source_id}/objects/{object_key}/discover` — schema discovery with no raw samples returned
- `POST /api/v1/sources/{source_id}/extract` — immutable extraction; requires `X-Organization-ID` and an object key body
- `POST /api/v1/profiles` — masked profile plus optional approved-baseline drift comparison
- `POST /api/v1/mappings/preview` — bounded mapping dry run with masked row errors
- `POST /api/v1/validations` — multi-category validation, quality dimensions, persisted results, and quarantine IDs; optional `mapping_id` and `lookup_ids` validate the mapped canonical records instead of the raw snapshot, and the response labels its `record_source`
- `POST /api/v1/quarantine/{quarantine_id}/resolve` — attributable resolution/waiver/correction metadata
- `POST /api/v1/matches/deterministic/synthetic` — organization-scoped deterministic linkage and synthetic truth evaluation
- `POST /api/v1/matches/probabilistic/synthetic` — explicit synthetic estimation, probabilities, gray-zone candidates, and model/run evidence
- `POST /api/v1/marts` — permission-gated governed mart build; optional `source_snapshot_id` and `mapping_id` register lineage back to the raw snapshot
- `POST /api/v1/exports` — permission-gated documented masked export with automatic mart-to-export lineage
- `GET /api/v1/lineage/{node_id}` — organization-scoped lineage trace; accepts a lineage node id or a snapshot, mart, or export identifier
- `POST /api/v1/orchestration/runs` — permission-gated asset run with partition and watermark
- `POST /api/v1/retention/apply` — dry-run-by-default retention enforcement
- `GET /api/v1/me` — current demo/OIDC-adapted actor
- `GET /api/v1/audit` — permission-gated organization audit events covering extraction, mapping previews, validation, matching, marts, exports, orchestration, and retention

Extraction returns run ID, snapshot ID, checksum, storage URI, row count, reuse flag, and cursor. Processing endpoints require an organization header and versioned configuration. In non-production demo mode, `X-Demo-User` selects `demo-admin` or `demo-viewer`; production must replace demo identity with verified OIDC infrastructure. Authorization is still enforced after authentication.
