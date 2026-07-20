# ADR 0009: Bounded Mapping DSL

Status: Accepted

Mapping YAML may invoke only registered transforms and governed lookup tables. Arbitrary executable expressions are prohibited. Plugins are process-registered code with tests; configuration may reference but never import code.
