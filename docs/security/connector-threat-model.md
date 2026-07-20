# Phase 4 Connector Threat Model

| Threat | Control |
|---|---|
| Path traversal | Resolve paths and require containment in an allowed root |
| Symlink escape | Reject source-file symlinks and recheck resolved containment |
| Oversized source | Per-source and global byte limits |
| Archive bomb/traversal | Member-count, uncompressed-size, and member-path checks |
| Spreadsheet formula injection | Preserve raw inputs; sanitize formula prefixes in later derived exports |
| SSRF | HTTPS by default, DNS resolution checks, private/link-local/loopback blocking, no redirects |
| URL credentials | Reject username/password in URLs; use secret references |
| Secret leakage | Resolve env references at runtime; never include values in configs, manifests, or logs |
| SQL injection | Validate identifiers and use SQLAlchemy expressions for values |
| Unbounded extraction | REST page cap, PostgreSQL row cap, timeouts, bounded retries |
| Duplicate raw evidence | SHA-256 content addressing and database uniqueness by source object/checksum |
| Silent overwrite | Atomic write then immutable reuse; no in-place payload mutation |
| Unsafe resume | Verify prior run organization and source before accepting its cursor |
| Raw-value error leak | Stable failure codes and safe summaries; logs contain IDs/counts only |
