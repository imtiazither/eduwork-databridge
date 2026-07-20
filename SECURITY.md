# Security Policy

## Supported versions

Only the most recent pre-1.0 release line receives security fixes. The current supported release candidate is v0.14.x.

## Reporting

Do not open a public issue for a vulnerability. Use GitHub private vulnerability reporting when enabled, or contact the repository owner through a private channel listed on the repository profile.

Include affected version/commit, reproduction steps, impact, and a minimal proof of concept that contains no real data.

## Scope

Secret exposure, cross-organization access, authorization bypass, unsafe file/archive/network handling, injection, dependency or workflow compromise, unauthorized identity merges, export leakage, audit tampering, and retention-path escape are security-relevant.

## Release evidence

The `release/` directory contains SBOMs, dependency-audit results, the targeted secret scan, package verification, environment gaps, and checksums. Docker image scan/sign/attestation evidence is produced by the tag release workflow and must not be claimed until that workflow succeeds.

## No sensitive data

Public demonstrations and tests use synthetic data only.
