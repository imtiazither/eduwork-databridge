# ADR 0013: Local-First Asset Orchestration with Dagster Semantics

Status: Accepted

A tested local asset engine provides dependencies, retries, watermarks, change hashes, skips, partitions, backfills, and run evidence. Dagster definitions expose equivalent asset topology and schedule semantics. A daemon/Kubernetes/managed deployment is deferred until justified.
