# Probabilistic Matching and Gray-Zone Review

Phase 9 generates candidates through governed blocking rules, calculates exact/string/date/numeric comparison features, and converts weighted evidence into illustrative match probabilities. Missing comparison values are neutral rather than automatic disagreement.

Synthetic truth may be used only through an explicit estimation call. Parameter estimates, model version, truth-set name, thresholds, run counts, feature evidence, candidate status, and cluster impact are persisted. Human decisions do not update the model automatically.

Statuses:

- `auto_match`: at or above the illustrative auto-match threshold and no trusted-ID conflict
- `review`: within the gray zone and requires human review
- `no_match`: below the review threshold
- `trusted_id_conflict`: different nonblank trusted IDs; automatic linking is prohibited

The default small synthetic demonstration creates 121 safe auto-match pairs and 29 gray-zone reviews. Auto-match precision is 1.0; potential recall with review is 1.0. These are synthetic evaluation results, not production guarantees or partner outcomes.
