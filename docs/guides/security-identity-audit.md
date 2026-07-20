# Identity, Authorization, Audit, and Retention

Phase 12 provides an isolated demo identity provider and an OIDC claims adapter for tokens whose signature and standard claims have already been verified by deployment infrastructure. The demo provider refuses production mode.

Authorization checks organization membership and explicit permissions. Seeded roles are administrator, data steward, publisher, and viewer. Protected APIs require permissions for matching, marts, exports, lineage, orchestration, audit, or retention.

Audit events record actor ID, action, resource type/ID, organization, correlation ID, and sanitized details. Sensitive attribute names are excluded.

Security middleware adds content-type, frame, referrer, permissions-policy, and CSP headers; enforces request-size limits; and applies a local per-identity rate limit. These controls support safe engineering but do not constitute regulatory certification.

Retention policies define raw, quarantine, export, and audit periods. Export deletion defaults to dry-run, is organization-scoped, accepts local file URIs only, and rejects paths outside the export root.
