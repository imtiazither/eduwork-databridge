# ADR 0005: Baseline Migration

Status: Accepted for the prototype baseline

The first Alembic revision creates the reviewed SQLAlchemy metadata as one baseline. All later schema changes must use explicit, reviewed Alembic operations and migration tests. This keeps the foundation reproducible without treating the schema as final for every deployment.
