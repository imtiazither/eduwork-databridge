# Identity, Authorization, Audit, and Retention

The security layer provides an isolated demo identity provider and an OIDC claims adapter for tokens whose signature and standard claims have already been verified by deployment infrastructure. The demo provider refuses production mode and missing credentials; local requests must explicitly select `demo-admin` or `demo-viewer`.

Authorization checks organization membership and explicit permissions. Seeded roles are administrator, data steward, publisher, and viewer. Organization/source metadata and source connection/discovery require `sources:read`. Snapshot profiling, mapping, validation, quarantine, matching, marts, exports, lineage, orchestration, audit, and retention enforce their explicit permissions. Snapshot ownership is checked before file reads and lineage attribution. Baseline profiles must belong to the same organization and source object.

Audit events record actor ID, action, resource type/ID, organization, correlation ID, and sanitized details. Sensitive attribute names are excluded. Match decisions and quarantine resolutions commit with their audit events, and their reviewers are derived from the authenticated actor.

Security middleware adds content-type, frame, referrer, permissions-policy, and CSP headers; enforces request-size limits; and applies a local per-identity rate limit. These controls support safe engineering but do not constitute regulatory certification.

Retention policies define raw, quarantine, export, and audit periods. Export deletion defaults to dry-run, is organization-scoped, accepts local file URIs only, and rejects paths outside the export root.
