# Architecture

EduWork DataBridge is a modular monolith with explicit package contracts and a local-first container topology.

```mermaid
flowchart LR
  SOURCES[HRIS / LMS / CRM / Assessment / Credential] --> CONNECT[Safe Read-only Connectors]
  CONNECT --> RAW[Immutable Raw Snapshots]
  RAW --> PROFILE[Masked Profiles + Drift]
  RAW --> MAP[Bounded Mapping DSL]
  MAP --> VALIDATE[Validation + Quarantine]
  MAP --> MATCH[Deterministic + Probabilistic Matching]
  VALIDATE --> MARTS[Governed Marts]
  MARTS --> EXPORTS[Masked CSV / Parquet Exports]
  RAW --> LINEAGE[Run + Field Lineage]
  MAP --> LINEAGE
  MARTS --> LINEAGE
  EXPORTS --> LINEAGE
  ORCH[Asset Orchestration] --> CONNECT
  ORCH --> PROFILE
  ORCH --> MARTS
  ID[Demo / OIDC-ready Identity] --> AUTHZ[Organization + Permissions]
  AUTHZ --> EXPORTS
  AUTHZ --> MATCH
  AUTHZ --> AUDIT[Audit Events]
```

![Synthetic field-lineage view](../assets/lineage-view.svg)

## Data zones

- Bronze: immutable raw snapshots and manifests
- Silver preparation: mapped, validated, quarantined, and identity-linked evidence
- Gold: documented marts and permission-gated exports
- Control plane: source, contract, run, rule, review, lineage, model, export, orchestration, retention, audit, and access metadata
