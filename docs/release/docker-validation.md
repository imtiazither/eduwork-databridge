# Docker and Registry Validation

The execution sandbox used for the reference release had no Docker daemon. Run this checklist on a Docker-enabled machine.

```bash
docker compose config
docker compose build --pull
docker compose up -d
docker compose ps
docker compose exec api uv run alembic current
curl -fsS http://localhost:8000/healthz
curl -fsS http://localhost:8000/readyz
```

## Image security

```bash
trivy image --severity HIGH,CRITICAL --exit-code 1 <image>
syft <image> -o cyclonedx-json > image.cdx.json
cosign sign <image-by-digest>
cosign verify <image-by-digest>
```

Record exact image digest, tool versions, scan results, signature bundle, verifier identity, date, and unresolved findings. Do not mark this gate complete from configuration inspection alone.
