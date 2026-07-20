# Data Dictionary

Generated from SQLAlchemy metadata. Do not edit by hand.

## assessment_attempts

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| assessment_id | CHAR(32) | no | FK → assessment_definitions.id |
| person_id | CHAR(32) | no | FK → persons.id |
| attempt_number | INTEGER | no |  |
| started_at | DATETIME | yes |  |
| submitted_at | DATETIME | yes |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## assessment_definitions

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| external_key | VARCHAR(255) | no |  |
| name | VARCHAR(255) | no |  |
| maximum_score | NUMERIC(12, 4) | yes |  |
| passing_score | NUMERIC(12, 4) | yes |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## assessment_results

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| attempt_id | CHAR(32) | no | FK → assessment_attempts.id |
| raw_score | NUMERIC(12, 4) | yes |  |
| normalized_score | NUMERIC(8, 6) | yes |  |
| outcome | VARCHAR(50) | yes |  |
| graded_at | DATETIME | yes |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## asset_runs

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| orchestration_key | VARCHAR(255) | no |  |
| asset_key | VARCHAR(255) | no |  |
| partition_key | VARCHAR(255) | yes |  |
| status | VARCHAR(30) | no |  |
| attempt_number | INTEGER | no |  |
| watermark_json | JSON | no |  |
| change_hash | VARCHAR(64) | yes |  |
| backfill_of_run_id | CHAR(32) | yes | FK → asset_runs.id |
| started_at | DATETIME | no |  |
| ended_at | DATETIME | yes |  |
| failure_code | VARCHAR(100) | yes |  |
| metadata_json | JSON | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## audit_events

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| occurred_at | DATETIME | no |  |
| organization_id | CHAR(32) | yes | FK → organizations.id |
| actor_id | CHAR(32) | yes |  |
| action | VARCHAR(100) | no |  |
| resource_type | VARCHAR(100) | no |  |
| resource_id | VARCHAR(255) | no |  |
| correlation_id | VARCHAR(100) | yes |  |
| details_json | JSON | no |  |
| id | CHAR(32) | no | PK |

## canonical_entity_versions

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| entity_type | VARCHAR(100) | no |  |
| entity_id | CHAR(32) | no |  |
| version_number | INTEGER | no |  |
| payload_json | JSON | no |  |
| valid_from | DATETIME | no |  |
| valid_to | DATETIME | yes |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## competency_alignments

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| competency_id | CHAR(32) | no | FK → competency_definitions.id |
| target_type | VARCHAR(50) | no |  |
| target_id | CHAR(32) | no |  |
| alignment_type | VARCHAR(50) | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## competency_definitions

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| external_key | VARCHAR(255) | no |  |
| name | VARCHAR(255) | no |  |
| description | TEXT | yes |  |
| framework_uri | VARCHAR(1000) | yes |  |
| parent_competency_id | CHAR(32) | yes | FK → competency_definitions.id |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## credential_awards

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| credential_definition_id | CHAR(32) | no | FK → credential_definitions.id |
| person_id | CHAR(32) | no | FK → persons.id |
| awarded_at | DATETIME | no |  |
| expires_at | DATETIME | yes |  |
| status | VARCHAR(30) | no |  |
| evidence_uri | VARCHAR(1000) | yes |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## credential_definitions

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| external_key | VARCHAR(255) | no |  |
| name | VARCHAR(255) | no |  |
| credential_type | VARCHAR(50) | no |  |
| issuer_name | VARCHAR(255) | yes |  |
| public_uri | VARCHAR(1000) | yes |  |
| expires | BOOLEAN | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## data_contracts

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| source_object_id | CHAR(32) | no | FK → source_objects.id |
| contract_key | VARCHAR(255) | no |  |
| version | VARCHAR(50) | no |  |
| schema_uri | VARCHAR(1000) | yes |  |
| schema_json | JSON | no |  |
| status | VARCHAR(30) | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## data_mart_snapshots

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| mart_key | VARCHAR(255) | no |  |
| version | VARCHAR(50) | no |  |
| storage_uri | VARCHAR(1000) | no |  |
| checksum_sha256 | VARCHAR(64) | no |  |
| row_count | INTEGER | no |  |
| dictionary_json | JSON | no |  |
| lineage_json | JSON | no |  |
| published_at | DATETIME | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## experience_events

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| source_system_id | CHAR(32) | no | FK → source_systems.id |
| person_id | CHAR(32) | yes | FK → persons.id |
| offering_id | CHAR(32) | yes | FK → learning_offerings.id |
| event_key | VARCHAR(255) | no |  |
| event_type | VARCHAR(100) | no |  |
| occurred_at | DATETIME | no |  |
| payload | JSON | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## export_definitions

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| export_key | VARCHAR(255) | no |  |
| version | VARCHAR(50) | no |  |
| format | VARCHAR(30) | no |  |
| contract_json | JSON | no |  |
| active | BOOLEAN | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## export_snapshots

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| export_definition_id | CHAR(32) | no | FK → export_definitions.id |
| storage_uri | VARCHAR(1000) | no |  |
| checksum_sha256 | VARCHAR(64) | no |  |
| row_count | INTEGER | yes |  |
| published_at | DATETIME | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## external_identities

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| person_id | CHAR(32) | no | FK → persons.id |
| source_system_id | CHAR(32) | no | FK → source_systems.id |
| identity_type | VARCHAR(50) | no |  |
| identity_value | VARCHAR(512) | no |  |
| identity_value_hash | VARCHAR(64) | no |  |
| trusted | BOOLEAN | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## ingestion_runs

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| source_system_id | CHAR(32) | no | FK → source_systems.id |
| status | VARCHAR(30) | no |  |
| started_at | DATETIME | yes |  |
| ended_at | DATETIME | yes |  |
| cursor_json | JSON | no |  |
| correlation_id | VARCHAR(100) | no |  |
| resume_from_run_id | CHAR(32) | yes | FK → ingestion_runs.id |
| attempt_number | INTEGER | no |  |
| failure_code | VARCHAR(100) | yes |  |
| failure_summary | VARCHAR(500) | yes |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## learning_offerings

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| program_id | CHAR(32) | yes | FK → learning_programs.id |
| external_key | VARCHAR(255) | no |  |
| name | VARCHAR(255) | no |  |
| offering_type | VARCHAR(50) | no |  |
| starts_at | DATETIME | yes |  |
| ends_at | DATETIME | yes |  |
| status | VARCHAR(30) | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## learning_programs

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| external_key | VARCHAR(255) | no |  |
| name | VARCHAR(255) | no |  |
| description | TEXT | yes |  |
| program_type | VARCHAR(50) | no |  |
| status | VARCHAR(30) | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## lineage_edges

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| from_node_id | CHAR(32) | no | FK → lineage_nodes.id |
| to_node_id | CHAR(32) | no | FK → lineage_nodes.id |
| relation_type | VARCHAR(50) | no |  |
| field_mapping_json | JSON | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## lineage_nodes

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| node_type | VARCHAR(50) | no |  |
| namespace | VARCHAR(255) | no |  |
| name | VARCHAR(500) | no |  |
| facets_json | JSON | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## lookup_tables

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| lookup_key | VARCHAR(255) | no |  |
| version | VARCHAR(50) | no |  |
| values_json | JSON | no |  |
| status | VARCHAR(30) | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## mapping_errors

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| mapping_execution_id | CHAR(32) | no | FK → mapping_executions.id |
| source_record_key | VARCHAR(255) | no |  |
| rule_sequence | INTEGER | no |  |
| target_field | VARCHAR(255) | no |  |
| error_code | VARCHAR(100) | no |  |
| explanation | TEXT | no |  |
| evidence_masked | TEXT | yes |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## mapping_executions

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| raw_snapshot_id | CHAR(32) | no | FK → raw_snapshots.id |
| mapping_key | VARCHAR(255) | no |  |
| mapping_version | VARCHAR(50) | no |  |
| status | VARCHAR(30) | no |  |
| dry_run | BOOLEAN | no |  |
| input_count | INTEGER | no |  |
| output_count | INTEGER | no |  |
| error_count | INTEGER | no |  |
| output_uri | VARCHAR(1000) | yes |  |
| started_at | DATETIME | no |  |
| ended_at | DATETIME | yes |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## mapping_rules

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| mapping_set_id | CHAR(32) | no | FK → mapping_sets.id |
| sequence | INTEGER | no |  |
| target_field | VARCHAR(255) | no |  |
| source_expression | VARCHAR(1000) | yes |  |
| transform_type | VARCHAR(100) | no |  |
| parameters_json | JSON | no |  |
| required | BOOLEAN | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## mapping_sets

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| mapping_key | VARCHAR(255) | no |  |
| version | VARCHAR(50) | no |  |
| canonical_entity | VARCHAR(100) | no |  |
| status | VARCHAR(30) | no |  |
| approved_by | CHAR(32) | yes |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## match_candidates

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| rule_set_id | CHAR(32) | no | FK → match_rule_sets.id |
| left_record_key | VARCHAR(255) | no |  |
| right_record_key | VARCHAR(255) | no |  |
| score | NUMERIC(8, 6) | yes |  |
| evidence_json | JSON | no |  |
| status | VARCHAR(30) | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## match_decisions

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| candidate_id | CHAR(32) | no | FK → match_candidates.id |
| decision | VARCHAR(30) | no |  |
| reason | TEXT | no |  |
| reviewer_id | CHAR(32) | no |  |
| decided_at | DATETIME | no |  |
| supersedes_decision_id | CHAR(32) | yes | FK → match_decisions.id |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## match_evaluations

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| rule_set_key | VARCHAR(255) | no |  |
| rule_set_version | VARCHAR(50) | no |  |
| truth_set_name | VARCHAR(255) | no |  |
| evaluated_at | DATETIME | no |  |
| total_records | INTEGER | no |  |
| predicted_links | INTEGER | no |  |
| true_positives | INTEGER | no |  |
| false_positives | INTEGER | no |  |
| false_negatives | INTEGER | no |  |
| precision | NUMERIC(8, 6) | no |  |
| recall | NUMERIC(8, 6) | no |  |
| coverage | NUMERIC(8, 6) | no |  |
| details_json | JSON | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## match_rule_sets

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| rule_set_key | VARCHAR(255) | no |  |
| version | VARCHAR(50) | no |  |
| entity_type | VARCHAR(100) | no |  |
| deterministic_rules_json | JSON | no |  |
| probabilistic_config_json | JSON | no |  |
| status | VARCHAR(30) | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## organization_units

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| parent_unit_id | CHAR(32) | yes | FK → organization_units.id |
| external_key | VARCHAR(255) | no |  |
| name | VARCHAR(255) | no |  |
| unit_type | VARCHAR(50) | no |  |
| effective_from | DATE | yes |  |
| effective_to | DATE | yes |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## organizations

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| name | VARCHAR(255) | no |  |
| organization_type | VARCHAR(50) | no |  |
| status | VARCHAR(30) | no |  |
| parent_organization_id | CHAR(32) | yes | FK → organizations.id |
| metadata_json | JSON | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## participations

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| person_id | CHAR(32) | no | FK → persons.id |
| offering_id | CHAR(32) | no | FK → learning_offerings.id |
| source_record_key | VARCHAR(255) | no |  |
| status | VARCHAR(30) | no |  |
| assigned_at | DATETIME | yes |  |
| started_at | DATETIME | yes |  |
| completed_at | DATETIME | yes |  |
| completion_percent | INTEGER | yes |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## permissions

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| permission_key | VARCHAR(150) | no |  |
| description | VARCHAR(1000) | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## persons

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| display_name | VARCHAR(255) | no |  |
| given_name | VARCHAR(150) | yes |  |
| family_name | VARCHAR(150) | yes |  |
| preferred_name | VARCHAR(150) | yes |  |
| status | VARCHAR(30) | no |  |
| effective_from | DATE | yes |  |
| effective_to | DATE | yes |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## probabilistic_models

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| model_key | VARCHAR(255) | no |  |
| version | VARCHAR(50) | no |  |
| status | VARCHAR(30) | no |  |
| comparison_config_json | JSON | no |  |
| parameters_json | JSON | no |  |
| review_low | NUMERIC(8, 6) | no |  |
| auto_match | NUMERIC(8, 6) | no |  |
| trained_on_truth_set | VARCHAR(255) | yes |  |
| trained_at | DATETIME | yes |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## probabilistic_runs

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| model_id | CHAR(32) | no | FK → probabilistic_models.id |
| status | VARCHAR(30) | no |  |
| candidate_count | INTEGER | no |  |
| auto_match_count | INTEGER | no |  |
| review_count | INTEGER | no |  |
| no_match_count | INTEGER | no |  |
| conflict_count | INTEGER | no |  |
| metrics_json | JSON | no |  |
| started_at | DATETIME | no |  |
| ended_at | DATETIME | yes |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## profile_comparisons

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| baseline_profile_id | CHAR(32) | no | FK → schema_profiles.id |
| current_profile_id | CHAR(32) | no | FK → schema_profiles.id |
| status | VARCHAR(30) | no |  |
| comparison_json | JSON | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## quarantine_records

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| ingestion_run_id | CHAR(32) | no | FK → ingestion_runs.id |
| validation_rule_id | CHAR(32) | no | FK → validation_rules.id |
| raw_snapshot_id | CHAR(32) | no | FK → raw_snapshots.id |
| source_record_key | VARCHAR(255) | no |  |
| field_name | VARCHAR(255) | yes |  |
| evidence_masked | TEXT | yes |  |
| explanation | TEXT | no |  |
| status | VARCHAR(30) | no |  |
| reviewer_id | CHAR(32) | yes |  |
| waiver_reason | TEXT | yes |  |
| resolution_note | TEXT | yes |  |
| resolved_at | DATETIME | yes |  |
| supersedes_quarantine_id | CHAR(32) | yes | FK → quarantine_records.id |
| corrected_snapshot_id | CHAR(32) | yes | FK → raw_snapshots.id |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## raw_snapshots

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| ingestion_run_id | CHAR(32) | no | FK → ingestion_runs.id |
| source_object_id | CHAR(32) | no | FK → source_objects.id |
| storage_uri | VARCHAR(1000) | no |  |
| checksum_sha256 | VARCHAR(64) | no |  |
| row_count | INTEGER | yes |  |
| schema_fingerprint | VARCHAR(64) | yes |  |
| manifest_json | JSON | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## retention_policies

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| policy_key | VARCHAR(255) | no |  |
| raw_days | INTEGER | no |  |
| quarantine_days | INTEGER | no |  |
| export_days | INTEGER | no |  |
| audit_days | INTEGER | no |  |
| active | BOOLEAN | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## role_assignments

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| person_id | CHAR(32) | no | FK → persons.id |
| organization_unit_id | CHAR(32) | yes | FK → organization_units.id |
| role_type | VARCHAR(50) | no |  |
| status | VARCHAR(30) | no |  |
| effective_from | DATE | yes |  |
| effective_to | DATE | yes |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## role_permissions

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| role_id | CHAR(32) | no | FK → roles.id |
| permission_id | CHAR(32) | no | FK → permissions.id |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## roles

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| role_key | VARCHAR(100) | no |  |
| name | VARCHAR(255) | no |  |
| description | VARCHAR(1000) | yes |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## schema_profiles

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| raw_snapshot_id | CHAR(32) | no | FK → raw_snapshots.id |
| profile_version | VARCHAR(50) | no |  |
| profile_json | JSON | no |  |
| baseline_profile_id | CHAR(32) | yes | FK → schema_profiles.id |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## source_objects

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| source_system_id | CHAR(32) | no | FK → source_systems.id |
| object_key | VARCHAR(255) | no |  |
| object_type | VARCHAR(50) | no |  |
| location_template | VARCHAR(1000) | yes |  |
| refresh_expectation | VARCHAR(100) | yes |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## source_systems

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| source_key | VARCHAR(100) | no |  |
| name | VARCHAR(255) | no |  |
| connector_type | VARCHAR(50) | no |  |
| owner_role | VARCHAR(255) | yes |  |
| data_classification | VARCHAR(30) | no |  |
| secret_reference | VARCHAR(500) | yes |  |
| active | BOOLEAN | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## user_organizations

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| user_id | CHAR(32) | no | FK → users.id |
| organization_id | CHAR(32) | no | FK → organizations.id |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## user_roles

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| user_id | CHAR(32) | no | FK → users.id |
| organization_id | CHAR(32) | no | FK → organizations.id |
| role_id | CHAR(32) | no | FK → roles.id |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## users

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| subject | VARCHAR(500) | no |  |
| email | VARCHAR(320) | yes |  |
| display_name | VARCHAR(255) | yes |  |
| active | BOOLEAN | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## validation_results

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| ingestion_run_id | CHAR(32) | no | FK → ingestion_runs.id |
| validation_rule_id | CHAR(32) | no | FK → validation_rules.id |
| passed | BOOLEAN | no |  |
| evaluated_count | INTEGER | no |  |
| failed_count | INTEGER | no |  |
| result_json | JSON | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

## validation_rules

| Column | Type | Nullable | Key/Reference |
|---|---|---:|---|
| organization_id | CHAR(32) | no | FK → organizations.id |
| rule_key | VARCHAR(255) | no |  |
| version | VARCHAR(50) | no |  |
| title | VARCHAR(255) | no |  |
| entity_name | VARCHAR(100) | no |  |
| severity | VARCHAR(30) | no |  |
| expression_type | VARCHAR(100) | no |  |
| expression_json | JSON | no |  |
| explanation | TEXT | no |  |
| remediation | TEXT | yes |  |
| active | BOOLEAN | no |  |
| id | CHAR(32) | no | PK |
| created_at | DATETIME | no |  |
| updated_at | DATETIME | no |  |

