from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    SecretStr,
    field_validator,
    model_validator,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, str_strip_whitespace=True)


class RetryPolicy(StrictModel):
    attempts: Annotated[int, Field(ge=1, le=10)] = 3
    initial_seconds: Annotated[float, Field(gt=0, le=60)] = 1.0
    maximum_seconds: Annotated[float, Field(gt=0, le=600)] = 30.0


class SourceObjectConfig(StrictModel):
    key: str
    object_type: Literal["file", "table", "api_resource"]
    location: str
    contract_version: str
    incremental_field: str | None = None
    sheet_name: str | None = None
    json_records_path: str | None = None
    primary_key: list[str] = Field(default_factory=list)
    options: dict[str, str | int | float | bool] = Field(default_factory=dict)


class SourceConfig(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    source_id: str
    name: str
    connector: Literal["csv", "xlsx", "json", "parquet", "rest", "postgresql"]
    owner_role: str
    data_classification: Literal["public", "internal", "confidential", "restricted"]
    secret_reference: SecretStr | None = None
    base_url: HttpUrl | None = None
    refresh_expectation: str | None = None
    max_bytes: Annotated[int, Field(gt=0, le=5 * 1024 * 1024 * 1024)] = 100 * 1024 * 1024
    allowed_roots: list[str] = Field(default_factory=lambda: ["data/synthetic"])
    request_timeout_seconds: Annotated[float, Field(gt=0, le=300)] = 30.0
    allow_private_network: bool = False
    retry: RetryPolicy = Field(default_factory=RetryPolicy)
    objects: Annotated[list[SourceObjectConfig], Field(min_length=1)]

    @field_validator("secret_reference")
    @classmethod
    def reject_literal_secret(cls, value: SecretStr | None) -> SecretStr | None:
        if value and value.get_secret_value().lower().startswith(("password=", "token=")):
            raise ValueError("Use a secret reference, never a literal secret")
        return value


class MappingRuleConfig(StrictModel):
    target: str
    source: str | None = None
    transform: Literal[
        "copy",
        "trim",
        "lower",
        "upper",
        "parse_datetime_utc",
        "lookup",
        "default",
        "concat",
        "split",
        "conditional",
        "sha256_pseudonymize",
        "plugin",
    ] = "copy"
    lookup: str | None = None
    default: str | int | float | bool | None = None
    parameters: dict[str, str | int | float | bool | list[str]] = Field(default_factory=dict)
    plugin: str | None = None
    required: bool = False


class MappingConfig(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    mapping_id: str
    source_contract: str
    canonical_entity: str
    rules: Annotated[list[MappingRuleConfig], Field(min_length=1)]


class ValidationRuleConfig(StrictModel):
    rule_id: str
    title: str
    entity: str
    severity: Literal["info", "warning", "error", "blocking"]
    rule_type: Literal[
        "schema",
        "required",
        "allowed_values",
        "unique",
        "range",
        "pattern",
        "reference",
        "temporal",
        "cross_source",
        "timeliness",
    ]
    fields: Annotated[list[str], Field(min_length=1)]
    parameters: dict[str, str | int | float | bool | list[str]] = Field(default_factory=dict)
    explanation: str
    remediation: str | None = None


class ValidationConfig(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    validation_set_id: str
    entity: str
    rules: Annotated[list[ValidationRuleConfig], Field(min_length=1)]


class PipelineConfig(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    pipeline_id: str
    organization_key: str
    sources: Annotated[list[str], Field(min_length=1)]
    mapping_sets: Annotated[list[str], Field(min_length=1)]
    validation_sets: Annotated[list[str], Field(min_length=1)]
    publish_targets: list[str] = Field(default_factory=list)


class DriftThresholdConfig(StrictModel):
    null_rate_delta: Annotated[float, Field(ge=0, le=1)] = 0.05
    distinct_rate_delta: Annotated[float, Field(ge=0, le=1)] = 0.10
    numeric_mean_relative_delta: Annotated[float, Field(ge=0)] = 0.20
    top_value_share_delta: Annotated[float, Field(ge=0, le=1)] = 0.15


class ProfileConfig(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    profile_id: str
    sample_limit: Annotated[int, Field(gt=0, le=1_000_000)] = 100_000
    top_values_limit: Annotated[int, Field(gt=0, le=100)] = 10
    mask_samples: bool = True
    thresholds: DriftThresholdConfig = Field(default_factory=DriftThresholdConfig)


class DeterministicMatchRuleConfig(StrictModel):
    rule_id: str
    priority: Annotated[int, Field(ge=1)]
    fields: Annotated[list[str], Field(min_length=1)]
    trusted: bool = False
    require_all: bool = True


class DeterministicMatchConfig(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    rule_set_id: str
    organization_field: str = "organization_id"
    record_key_field: str = "record_key"
    rules: Annotated[list[DeterministicMatchRuleConfig], Field(min_length=1)]


class BlockingRuleConfig(StrictModel):
    rule_id: str
    fields: Annotated[list[str], Field(min_length=1)]
    require_all: bool = True


class ComparisonFieldConfig(StrictModel):
    field: str
    method: Literal["exact", "string_similarity", "date_distance", "numeric_distance"]
    weight: Annotated[float, Field(gt=0)] = 1.0
    agreement_probability: Annotated[float, Field(gt=0, lt=1)] = 0.95
    random_agreement_probability: Annotated[float, Field(gt=0, lt=1)] = 0.10
    tolerance: Annotated[float, Field(ge=0)] = 0.0


class ProbabilisticMatchConfig(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    model_id: str
    organization_field: str = "organization_id"
    record_key_field: str = "record_key"
    blocking_rules: Annotated[list[BlockingRuleConfig], Field(min_length=1)]
    comparisons: Annotated[list[ComparisonFieldConfig], Field(min_length=1)]
    prior_match_probability: Annotated[float, Field(gt=0, lt=1)] = 0.02
    review_low: Annotated[float, Field(gt=0, lt=1)] = 0.70
    auto_match: Annotated[float, Field(gt=0, lt=1)] = 0.95
    max_candidates: Annotated[int, Field(gt=0, le=5_000_000)] = 500_000

    @model_validator(mode="after")
    def validate_thresholds(self) -> "ProbabilisticMatchConfig":
        if self.review_low >= self.auto_match:
            raise ValueError("review_low must be lower than auto_match")
        return self


class MartDefinitionConfig(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    mart_id: str
    version: str
    entity: Literal["training_participation", "credential_status", "quality_trend"]
    fields: Annotated[list[str], Field(min_length=1)]
    definitions: dict[str, str]


class ExportConfig(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    export_id: str
    version: str
    mart_id: str
    format: Literal["csv", "parquet"]
    fields: Annotated[list[str], Field(min_length=1)]
    masked_fields: list[str] = Field(default_factory=list)
    retention_days: Annotated[int, Field(gt=0, le=3650)] = 30


class AssetScheduleConfig(StrictModel):
    asset_key: str
    cron: str | None = None
    partitions: list[str] = Field(default_factory=list)
    max_attempts: Annotated[int, Field(ge=1, le=10)] = 3


class OrchestrationConfig(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    orchestration_id: str
    assets: Annotated[list[AssetScheduleConfig], Field(min_length=1)]


class RetentionPolicyConfig(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    policy_id: str
    raw_days: Annotated[int, Field(gt=0, le=3650)]
    quarantine_days: Annotated[int, Field(gt=0, le=3650)]
    export_days: Annotated[int, Field(gt=0, le=3650)]
    audit_days: Annotated[int, Field(gt=0, le=3650)]
