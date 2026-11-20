FROM python:3.12-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
WORKDIR /app

# Require at least the Debian security fix for CVE-2026-85091.
RUN apt-get update \
    && apt-get install -y --no-install-recommends --only-upgrade zlib1g \
    && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' zlib1g)" ge '1:1.3.dfsg+really1.3.1-1+deb13u1' \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.13.4
COPY pyproject.toml uv.lock README.md ./
COPY packages ./packages
COPY migrations ./migrations
COPY alembic.ini ./
COPY configs ./configs
COPY data ./data
RUN uv sync --frozen --no-dev && mkdir -p var/raw var/mapped var/marts var/exports var/lineage

EXPOSE 8000
CMD ["sh", "-c", "uv run alembic upgrade head && uv run python -m eduwork_databridge.seed && uv run uvicorn eduwork_databridge.main:app --host 0.0.0.0 --port 8000"]
