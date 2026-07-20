# Connector and Immutable Ingestion Guide

## Implemented connectors

- CSV
- XLSX
- JSON
- Parquet
- REST/JSON
- PostgreSQL

Each connector implements connection testing, schema discovery, extraction, cursor reporting, and close. File connectors preserve the original bytes. REST and database connectors serialize the extracted record batch deterministically.

## Source configuration

Source YAML is strict and versioned. It contains a connector type, owner, classification, secret reference, limits, allowed roots or base URL, retry policy, and one or more objects. Literal secrets are rejected; the reference implementation resolves `env://VARIABLE_NAME` only.

## Raw snapshots

The raw store writes content-addressed payloads under:

```text
var/raw/<source_id>/<object_key>/<checksum-prefix>/<sha256>.<extension>
```

A sidecar manifest records source and object IDs, connector and contract versions, extraction time, SHA-256, row count, schema fingerprint, storage URI, content type, and cursor. Existing content is reused and never overwritten.

## API

- `POST /api/v1/sources/{source_id}/test`
- `GET /api/v1/sources/{source_id}/objects/{object_key}/discover`
- `POST /api/v1/sources/{source_id}/extract`

Extraction requires `X-Organization-ID` and registered source/object metadata. Resume requests may identify a prior run; the service verifies organization and source before using the prior cursor.

## Security defaults

- Files must resolve under configured roots, use an allowed extension, and stay within the size limit.
- XLSX archives are checked for traversal, excessive members, and excessive expansion.
- REST defaults to HTTPS, does not follow redirects, blocks credentials in URLs, and blocks private, loopback, link-local, reserved, multicast, and unspecified addresses unless the development override is explicitly enabled.
- Retries are bounded and restricted to safe network failures, 429, and server errors.
- PostgreSQL table and incremental-field identifiers are strictly validated; values use SQLAlchemy expressions rather than string concatenation.
- Source secrets and raw record values are not logged.

## PostgreSQL verification note

The connector contract and incremental-query behavior are tested through a local SQLAlchemy fixture. A live PostgreSQL integration test should be run through Docker Compose on a Docker-enabled machine before public release.
