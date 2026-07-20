# Deterministic Identity Matching Guide

Phase 8 normalizes Unicode, whitespace, email, phone, and source IDs, then applies rules in priority order.

1. Trusted exact identifiers link first.
2. Approved composite exact rules may link remaining records.
3. A composite rule cannot merge clusters carrying disjoint trusted identifiers; it creates a `trusted_id_conflict` candidate instead.
4. Matching input must contain one organization only and unique record keys.

Candidates persist only field fingerprints and rule IDs, not raw comparison values. Human decisions are append-only: a new decision may supersede a prior decision, preserving both.

The synthetic evaluation uses pairwise precision, recall, false positives, false negatives, and coverage. With the v0.8.0 small fixture and default rule set, the measured demonstration is precision 1.0, recall 0.91666667, and coverage 0.93495935. These are synthetic benchmark results, not partner or operational outcomes.

Probabilistic matching, learned thresholds, and gray-zone scoring begin in Phase 9.
