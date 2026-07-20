# Release Risk Register

| Risk | Current control | Remaining action |
|---|---|---|
| False identity merge | Trusted-ID vetoes, thresholds, gray-zone review, reversible decisions | Calibrate with representative approved labels |
| Cross-organization access | Organization-scoped services and authorization tests | Add production database RLS if required |
| Data leakage | Synthetic public data, masking, secret/log filters, export allowlists | Deployment review and DLP controls |
| SSRF or unsafe files | URL/IP checks, no redirects, roots, size/archive limits | Repeat penetration review in target network |
| Schema/model drift | Masked profiles, baselines, threshold evidence | Approve workflow-specific thresholds |
| Supply-chain compromise | Lockfiles, SBOMs, CI scans, checksums | Run container scan and signing in Docker/registry environment |
| Unreproducible release | Clean-clone, generated-artifact checks, package build | Preserve signed tag and immutable release artifacts |
| Unsupported impact claim | Claims register, maturity notices, synthetic labels | Use real measured pilot evidence only |
| Demo identity misuse | Demo provider refuses production | Configure and verify real OIDC deployment |
| Retention deletion error | Dry-run default, organization/path restrictions | Approve policy and backup in target environment |
