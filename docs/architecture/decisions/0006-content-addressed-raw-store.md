# ADR 0006: Content-Addressed Immutable Raw Store

Status: Accepted

Raw payloads are identified by SHA-256 and stored under source/object/checksum paths. Existing bytes are reused, never overwritten. A sidecar manifest records extraction and schema metadata. The control database enforces uniqueness for each source object and checksum.
