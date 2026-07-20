.PHONY: install lock lint format type test test-fast test-migration frontend frontend-test frontend-build generate generate-synthetic generate-check check docs-build benchmark-smoke sbom security-scan package-build package-verify release-checksums release-verify api ui seed migrate phase8-demo clean

install:
	uv sync --frozen --extra dev
	cd apps/reviewer-ui && npm ci

lock:
	uv lock
	cd apps/reviewer-ui && npm install --package-lock-only

lint:
	uv run ruff check .
	uv run ruff format --check .

type:
	uv run mypy packages/eduwork_databridge scripts

test:
	uv run pytest

test-fast:
	uv run pytest -m "not integration"

test-migration:
	uv run pytest tests/integration/test_migration.py

frontend-test:
	cd apps/reviewer-ui && npm test -- --run

frontend-build:
	cd apps/reviewer-ui && npm run build

frontend: frontend-test frontend-build

generate: generate-synthetic
	uv run python scripts/export_json_schemas.py
	uv run python scripts/generate_data_dictionary.py

generate-synthetic:
	uv run python scripts/generate_synthetic_data.py --preset small --seed 20260719
	uv run python scripts/generate_synthetic_data.py --preset medium --seed 20260719

generate-check:
	uv run python scripts/export_json_schemas.py --check
	uv run python scripts/generate_data_dictionary.py --check
	uv run python scripts/verify_synthetic_data.py

check: lint type test frontend generate-check

api:
	uv run uvicorn eduwork_databridge.main:app --reload

ui:
	cd apps/reviewer-ui && npm run dev

seed:
	uv run python -m eduwork_databridge.seed

migrate:
	uv run alembic upgrade head

phase8-demo: migrate seed
	uv run python scripts/run_phase8_demo.py

docs-build:
	uv run mkdocs build --strict

benchmark-smoke:
	mkdir -p benchmark-results
	uv run python scripts/run_benchmark.py --preset small --seed 20260719 --output benchmark-results/smoke.json
	uv run python scripts/verify_benchmark.py --current benchmark-results/smoke.json --baseline benchmark-baseline/small-v0.14.0.json --budgets benchmark-baseline/budgets.json

sbom:
	mkdir -p release/sbom
	uv export --format cyclonedx1.5 --no-dev --no-emit-project --frozen --output-file release/sbom/python-runtime.cdx.json
	npm --prefix apps/reviewer-ui sbom --package-lock-only --sbom-format cyclonedx > release/sbom/frontend.cdx.json
	npm --prefix apps/reviewer-ui sbom --package-lock-only --sbom-format spdx > release/sbom/frontend.spdx.json

security-scan:
	mkdir -p release/security
	uv run pip-audit --local --format json --output release/security/pip-audit.json
	npm --prefix apps/reviewer-ui audit --json > release/security/npm-audit.json
	uv run python scripts/scan_secrets.py --root . --output release/security/secret-scan.json

package-build:
	rm -rf release/packages
	mkdir -p release/packages
	uv run python -m build --outdir release/packages

package-verify:
	uv run python scripts/verify_packages.py
	uv run python scripts/verify_wheel_install.py

release-checksums:
	uv run python scripts/generate_release_checksums.py
	uv run python scripts/generate_release_checksums.py --check

release-verify: check docs-build benchmark-smoke sbom security-scan package-build package-verify
	uv run python scripts/verify_release.py
	$(MAKE) release-checksums

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov apps/reviewer-ui/dist
