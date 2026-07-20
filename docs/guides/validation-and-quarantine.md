# Validation and Quarantine Guide

Phase 7 supports structural, completeness, validity, uniqueness, referential, temporal, cross-source, and timeliness rules. Every rule carries a stable ID, severity, explanation, and remediation guidance.

Validation persists one aggregate result per rule and one quarantine row per failed record/rule. Evidence is masked. Quality dimensions report evaluated, failed, and pass-rate counts; no combined score is presented as universal truth.

Blocking failures prevent later publication but do not rewrite source evidence. Quarantine statuses include open, acknowledged, corrected upstream, corrected mapping, waived, and closed. Resolution requires a reviewer and note. Waivers preserve a reason. Corrected snapshots must remain in the same organization scope. Reprocessing creates a new quarantine row linked through `supersedes_quarantine_id`.
