# Local Deployment

## Docker Compose

```bash
cp .env.example .env
docker compose config
docker compose up --build
```

Services:

- PostgreSQL control plane
- FastAPI application
- worker shell / orchestration entry point
- reviewer UI
- persistent `pipeline-data` volume for raw, mapped, mart, export, and lineage artifacts

## Required post-start checks

```bash
curl -fsS http://localhost:8000/healthz
curl -fsS http://localhost:8000/readyz
curl -fsS -H 'X-Demo-User: demo-admin' http://localhost:8000/api/v1/me
```

## Production boundary

- Disable demo identity.
- Verify OIDC signatures upstream and restrict issuer/audience.
- Use managed secrets, TLS, managed PostgreSQL/object storage, private networking, backups, monitoring, and approved retention.
- Complete the Docker/registry-signing checklist before deployment.
