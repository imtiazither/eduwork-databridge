# Orchestration and Telemetry

Phase 11 includes Dagster asset definitions for external inspection plus a local-first asset engine used by tests and the API.

The local engine supports dependencies, partitions, bounded attempts, failure hooks, watermarks, change hashes, unchanged-input skipping, backfill links, safe run metadata, and persisted run status. Dependency results are passed through an explicit context. Only allowlisted metadata keys are persisted.

OpenTelemetry-compatible traces, counters, and duration histograms are emitted through a local provider. Attributes containing secret, token, password, raw, record, email, or name indicators are discarded. String attributes are truncated.

Dagster definitions expose raw snapshot, profile, validated, and mart assets plus a daily job/schedule. Production deployment of a Dagster daemon or managed service is not claimed in this phase.
