# Configuration Reference

Configuration is strict, versioned YAML validated through Pydantic and exported JSON Schema. Literal secrets are forbidden; use a secret reference resolved by the deployment environment.

Supported Phase 12 configuration models:

- SourceConfig
- MappingConfig
- ValidationConfig
- PipelineConfig
- ProfileConfig
- DeterministicMatchConfig
- ProbabilisticMatchConfig
- MartDefinitionConfig
- ExportConfig
- OrchestrationConfig
- RetentionPolicyConfig

Source, profile, mapping, validation, deterministic/probabilistic matching, marts, exports, orchestration, and retention configurations are executable through bounded services. Lookup files use a separate strict `lookup_id`, `version`, and `values` structure. Probabilistic thresholds and demo schedules remain illustrative until deployment-specific review.
