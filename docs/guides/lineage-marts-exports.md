# Lineage, Marts, and Governed Exports

Phase 10 stores dataset, job, field, mart, and export lineage nodes/edges. Mapping rules link raw snapshots to canonical target fields. Exports link mart snapshots to immutable export snapshots. OpenLineage-compatible JSON events describe jobs, runs, inputs, outputs, and organization facets without raw values.

Implemented marts:

- training participation: documented participation fields plus completion/progress flags
- credential status: documented awards plus current/expired status
- data-quality trend: evaluated/failed counts plus transparent pass rate

Mart snapshots are Parquet, content-addressed, checksum-protected, versioned, and accompanied by a field dictionary and lineage metadata.

Exports support CSV and Parquet. Only fields documented by the source mart may be exported. Configured fields are fingerprint-masked. CSV formula prefixes are neutralized. Each export records definition/version, checksum, row count, dictionary, source mart, field lineage, and retention period. `exports:write` is required.
