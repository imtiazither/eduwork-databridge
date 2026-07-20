import json
import shutil
import subprocess
from pathlib import Path

from scripts.verify_backup_restore import verify as verify_backup_restore
from scripts.verify_benchmark import verify as verify_benchmark


def test_benchmark_baseline_and_regression_budgets() -> None:
    verify_benchmark(
        Path("benchmark-results/current-v0.14.0.json"),
        Path("benchmark-baseline/small-v0.14.0.json"),
        Path("benchmark-baseline/budgets.json"),
    )


def test_docs_video_sboms_scans_and_packages_exist(tmp_path: Path) -> None:
    site = tmp_path / "site"
    subprocess.run(
        ["mkdocs", "build", "--strict", "--site-dir", str(site)],
        check=True,
    )
    video = Path("docs/assets/eduwork-databridge-walkthrough.mp4")
    pip_audit_path = Path("release/security/pip-audit.json")
    npm_audit_path = Path("release/security/npm-audit.json")
    secret_scan_path = Path("release/security/secret-scan.json")
    package_verification_path = Path("release/packages/package-verification.json")
    required = [
        site / "index.html",
        Path("docs/assets/reviewer-console.svg"),
        Path("docs/assets/lineage-view.svg"),
        video,
        Path("release/sbom/python-runtime.cdx.json"),
        Path("release/sbom/frontend.cdx.json"),
        Path("release/sbom/frontend.spdx.json"),
        pip_audit_path,
        npm_audit_path,
        secret_scan_path,
        package_verification_path,
    ]
    assert all(path.exists() and path.stat().st_size > 0 for path in required)
    assert video.read_bytes()[4:8] == b"ftyp"
    ffprobe = shutil.which("ffprobe")
    if ffprobe is not None:
        probe = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(video),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        assert float(json.loads(probe.stdout)["format"]["duration"]) == 36.0
    pip_audit = json.loads(pip_audit_path.read_text(encoding="utf-8"))
    assert not [
        vulnerability
        for dependency in pip_audit["dependencies"]
        for vulnerability in dependency.get("vulns", [])
    ]
    npm_audit = json.loads(npm_audit_path.read_text(encoding="utf-8"))
    assert npm_audit["metadata"]["vulnerabilities"]["total"] == 0
    assert json.loads(secret_scan_path.read_text(encoding="utf-8"))["findings"] == []
    assert json.loads(package_verification_path.read_text(encoding="utf-8"))["status"] == "passed"


def test_backup_restore_reference_flow(tmp_path: Path) -> None:
    result = verify_backup_restore(tmp_path / "backup-restore.json")
    assert result["status"] == "passed"
    assert result["organization_count"] == 1
