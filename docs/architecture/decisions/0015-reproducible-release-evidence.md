# ADR 0015: Reproducible Release Evidence

Status: Accepted

The release candidate preserves lockfiles, generated schemas, benchmark environment/results/budgets, Python and frontend SBOMs, dependency and secret-scan results, package artifacts, checksums, documentation/video assets, and environment gaps. CI repeats the feasible gates and tag releases add Docker scan/sign/attestation steps.
