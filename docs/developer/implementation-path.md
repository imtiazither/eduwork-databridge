# Implementation Path

## Package boundaries

- `connectors`: read-only source interfaces and safety checks
- `ingestion`: immutable snapshots and record readers
- `profiling`: masked profiles and drift evidence
- `mapping`: bounded mapping compiler/executor and lookups
- `validation`: rules, quality dimensions, quarantine, and resolution
- `matching`: deterministic and probabilistic linkage evidence
- `lineage`: run/field lineage and OpenLineage-compatible events
- `marts` and `publishing`: governed datasets, exports, and retention
- `orchestration` and `observability`: assets, retries, watermarks, backfills, traces, and metrics
- `security`: identity, authorization, audit, middleware, and claim boundaries

## Safe extension sequence

1. Define the use case and data owner.
2. Add a strict source contract and synthetic fixture.
3. Implement the smallest connector or adapter change.
4. Profile and map with explicit versions.
5. Add validation and failure examples.
6. Add lineage and authorization.
7. Add unit, integration, API, security, and regression tests.
8. Update docs, benchmark, SBOM, changelog, and migration evidence.

Avoid adding frameworks or services unless they solve a measured problem that existing modules cannot.
