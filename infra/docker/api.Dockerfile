FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
WORKDIR /app

RUN pip install --no-cache-dir uv==0.11.29
COPY pyproject.toml uv.lock README.md ./
COPY packages ./packages
COPY migrations ./migrations
COPY alembic.ini ./
COPY configs ./configs
COPY data ./data
RUN uv sync --frozen --no-dev && mkdir -p var/raw var/mapped var/marts var/exports var/lineage

EXPOSE 8000
CMD ["sh", "-c", "uv run alembic upgrade head && uv run python -m eduwork_databridge.seed && uv run uvicorn eduwork_databridge.main:app --host 0.0.0.0 --port 8000"]
