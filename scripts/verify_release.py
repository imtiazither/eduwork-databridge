import json
import re
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Any, cast

from verify_benchmark import verify as verify_benchmark

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.15.0"


def load_json(path: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((ROOT / path).read_text(encoding="utf-8")))


def verify() -> dict[str, Any]:
    checks: dict[str, str] = {}
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package = load_json("apps/reviewer-ui/package.json")
    init_text = (ROOT / "packages/eduwork_databridge/eduwork_databridge/__init__.py").read_text(
        encoding="utf-8"
    )
    versions = {
        str(project["project"]["version"]),
        str(package["version"]),
        re.search(r'__version__ = "([^"]+)"', init_text).group(1),  # type: ignore[union-attr]
    }
    if versions != {VERSION}:
        raise SystemExit(f"Version mismatch: {versions}")
    checks["version_consistency"] = "passed"

    required = [
        "mkdocs.yml",
        "docs/index.md",
        "docs/PROJECT_OVERVIEW.md",
        "docs/evaluator/30-minute-tour.md",
        "docs/assets/eduwork-databridge-walkthrough.mp4",
        "benchmark-baseline/small-v0.14.0.json",
        "benchmark-baseline/budgets.json",
        "release/sbom/python-runtime.cdx.json",
        "release/sbom/frontend.cdx.json",
        "release/sbom/frontend.spdx.json",
        "release/security/pip-audit.json",
        "release/security/npm-audit.json",
        "release/security/secret-scan.json",
        "release/packages/package-verification.json",
        "release/packages/wheel-install-verification.json",
        "release/backup-restore-verification.json",
        "release/benchmark-verification.json",
        "release/environment-gaps.json",
        "docs/release/external-review-checklist.md",
        "docs/release/release-candidate-checklist.md",
        "docs/release/risk-register.md",
        "docs/release/claim-boundaries.md",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    if missing:
        raise SystemExit("Release artifacts missing: " + ", ".join(missing))
    checks["required_artifacts"] = "passed"

    verify_benchmark(
        ROOT / "benchmark-baseline/small-v0.14.0.json",
        None,
        None,
    )
    checks["benchmark_integrity"] = "passed"

    pip_audit = load_json("release/security/pip-audit.json")
    pip_vulnerabilities = [
        vulnerability
        for dependency in pip_audit["dependencies"]
        for vulnerability in dependency.get("vulns", [])
    ]
    if pip_vulnerabilities:
        raise SystemExit("Python dependency audit contains vulnerabilities")
    npm_audit = load_json("release/security/npm-audit.json")
    if int(npm_audit["metadata"]["vulnerabilities"]["total"]) != 0:
        raise SystemExit("Frontend dependency audit contains vulnerabilities")
    if load_json("release/security/secret-scan.json")["findings"]:
        raise SystemExit("Targeted secret scan contains findings")
    checks["security_scans"] = "passed"

    for path in [
        "release/sbom/python-runtime.cdx.json",
        "release/sbom/frontend.cdx.json",
        "release/sbom/frontend.spdx.json",
    ]:
        document = load_json(path)
        if not document:
            raise SystemExit(f"SBOM is empty: {path}")
    checks["sboms"] = "passed"

    if load_json("release/packages/package-verification.json")["status"] != "passed":
        raise SystemExit("Package verification did not pass")
    if load_json("release/packages/wheel-install-verification.json")["status"] != "passed":
        raise SystemExit("Wheel installation verification did not pass")
    checks["packages"] = "passed"

    if load_json("release/backup-restore-verification.json")["status"] != "passed":
        raise SystemExit("Backup/restore verification did not pass")
    if load_json("release/benchmark-verification.json")["status"] != "passed":
        raise SystemExit("Benchmark regression verification did not pass")
    checks["backup_restore_and_regression"] = "passed"

    video_path = ROOT / "docs/assets/eduwork-databridge-walkthrough.mp4"
    if video_path.read_bytes()[4:8] != b"ftyp":
        raise SystemExit("Demo video is not a valid MP4 container")
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        checks["demo_video"] = "passed_format_only_no_ffprobe"
    else:
        probe = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_name,width,height",
                "-of",
                "json",
                str(video_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        video = json.loads(probe.stdout)
        if float(video["format"]["duration"]) < 30:
            raise SystemExit("Demo video is too short")
        checks["demo_video"] = "passed_with_ffprobe"

    gaps = load_json("release/environment-gaps.json")
    if gaps["docker_compose_runtime_test"] != "not_run_no_daemon":
        raise SystemExit("Environment-gap record is inconsistent")
    checks["environment_gaps_documented"] = "passed"

    result = {
        "project": "EduWork DataBridge",
        "version": VERSION,
        "status": "passed_with_documented_environment_gaps",
        "checks": checks,
        "checksums": "generated_after_verification",
    }
    output = ROOT / "release/release-verification.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
