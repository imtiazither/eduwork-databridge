# Troubleshooting

## Generated artifact drift

Run:

```bash
make generate
make generate-check
```

Commit the regenerated schemas, data dictionary, and synthetic manifests with the source change.

## Migration failure

- Confirm `EDUWORK_DATABASE_URL`.
- Run `uv run alembic current` and `uv run alembic history`.
- Test upgrade/downgrade on a copy, never an unbacked production database.

## Source rejected

Check allowed roots, file size, extension, archive limits, HTTPS/private-network policy, row/page limits, and `env://` secret references.

## Mapping errors

Inspect masked row issues, rule sequence, lookup version, required fields, datetime parsing, and plugin registry. Configuration cannot import executable code.

## Export forbidden

Confirm organization scope, `exports:write`, documented mart fields, masking policy, and retention configuration.

## Docker unavailable

Use the host-based clean-clone path (`uv`, npm, SQLite) and record Docker/live PostgreSQL/signing as outstanding environment checks. Do not claim those checks passed.
