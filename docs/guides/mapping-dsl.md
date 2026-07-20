# Mapping DSL Guide

Phase 6 compiles strict YAML into an allowlisted transformation plan. It rejects duplicate targets, unavailable lookups, unregistered plugins, and pseudonymization without a named context salt.

Built-in transforms: copy, trim, lower, upper, UTC datetime parsing, lookup, default, concat, split, conditional, SHA-256 pseudonymization, and registered plugin.

Arbitrary Python, SQL, templates, and expressions in YAML are prohibited. Plugins are supplied by the host process through an explicit registry and are never imported from configuration.

Dry runs limit input rows, return mapped outputs and masked row-level issues, and persist execution evidence without publishing output files. Non-dry runs write a versioned derived JSON artifact while preserving raw snapshots.

Lookup files contain exactly `lookup_id`, `version`, and `values`. Mapping diffs report added, removed, and changed target rules.
