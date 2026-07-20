# ADR 0005: Phase 2 Baseline Migration

Status: Accepted for the prototype baseline

The first Alembic revision creates the reviewed SQLAlchemy metadata as one baseline. All later schema changes must use explicit, reviewed Alembic operations and migration tests. This keeps Phase 2 reproducible without pretending the schema is production-final.
