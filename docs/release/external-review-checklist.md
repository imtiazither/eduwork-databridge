# External Technical Review Checklist

A reviewer should be independent of the implementation work and should identify their role and basis for evaluation.

## Architecture and scope

- [ ] Central source-to-export flow is coherent
- [ ] Package boundaries match the architecture
- [ ] Deferred features and pre-production limits are explicit
- [ ] Public/private repository boundary is credible

## Data and algorithms

- [ ] Synthetic fixtures are reproducible and contain no real data
- [ ] Mapping/validation rules are explainable and versioned
- [ ] Identity matching prevents cross-organization links and trusted-ID conflicts
- [ ] Probabilistic parameters and thresholds are labeled synthetic
- [ ] Marts and exports contain only documented fields

## Security and operations

- [ ] Authorization checks organization and permission
- [ ] Audit/telemetry/logging exclude sensitive values
- [ ] File/network/SQL/export/retention protections have negative tests
- [ ] Migrations, backup/restore, retries, backfills, and checksums are reproducible
- [ ] Dependencies, SBOMs, scans, and release evidence are complete

## Review output

Record reviewed commit/tag, commands run, findings, severity, limitations, and disposition. Do not provide generic praise or legal conclusions.
