# Release Candidate Checklist

## Source and tests

- [ ] Clean clone installs from committed lockfiles
- [ ] Ruff, format, strict mypy, pytest coverage gate, frontend tests/build pass
- [ ] Generated schemas, dictionary, manifests, docs, and benchmark checks pass
- [ ] Migration upgrade/downgrade and backup/restore pass
- [ ] Complete synthetic demo passes

## Supply chain

- [ ] Python CycloneDX SBOM generated from `uv.lock`
- [ ] Frontend CycloneDX and SPDX SBOMs generated from `package-lock.json`
- [ ] Dependency audit and targeted secret scan results recorded
- [ ] Wheel and source distribution built and inspected
- [ ] Release checksums generated
- [ ] Docker image scan/sign/attestation executed or explicitly marked outstanding

## Product evidence

- [ ] Documentation site builds in strict mode
- [ ] 30-minute evaluator path works
- [ ] Demo video and screenshots contain synthetic content only
- [ ] Benchmark records environment, preset, results, budgets, and limitations
- [ ] Changelog, roadmap, release manifest, risk register, and maturity claims agree

## Deployment-dependent gates

- [ ] Docker Compose starts and passes health checks
- [ ] Live PostgreSQL connector test passes
- [ ] Registry image is scanned, signed, and verified
- [ ] OIDC integration and authorization are reviewed
- [ ] Backup/restore is repeated in the target environment
