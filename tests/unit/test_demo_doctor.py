import subprocess
from pathlib import Path
from unittest.mock import Mock

from scripts import demo_doctor as doctor


def test_missing_tool_has_actionable_remedy(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda name: None)
    result = doctor.tool_version("node", (24, 0, 0))
    assert not result.ok
    assert "nodejs.org" in result.remedy


def test_tool_version_and_command_failure(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda name: f"/tools/{name}")
    run = Mock(return_value=subprocess.CompletedProcess([], 0, "v24.19.0\n", ""))
    monkeypatch.setattr(doctor.subprocess, "run", run)
    assert doctor.tool_version("node", (24, 0, 0)).ok
    run.return_value = subprocess.CompletedProcess([], 0, "v23.0.0", "")
    assert not doctor.tool_version("node", (24, 0, 0)).ok
    run.return_value = subprocess.CompletedProcess([], 0, "unrecognized", "")
    assert not doctor.tool_version("node", (24, 0, 0)).ok
    run.side_effect = subprocess.TimeoutExpired("node", 15)
    assert not doctor.tool_version("node", (24, 0, 0)).ok


def test_port_validation_and_occupied_port():
    assert not doctor.port_check("API", 80).ok
    with doctor.socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        assert not doctor.port_check("API", port).ok
    assert doctor.port_check("API", port).ok


def test_missing_checkout_and_duplicate_ports(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        doctor, "tool_version", lambda name, minimum: doctor.Check(name, True, "present")
    )
    checks = doctor.inspect(tmp_path, 65531, 65531)
    assert not next(check for check in checks if check.name == "Project files").ok
    assert not next(check for check in checks if check.name == "Separate ports").ok


def test_report_is_readable_and_machine_readable(capsys):
    checks = [
        doctor.Check("Python", True, "3.12"),
        doctor.Check("uv", False, "Missing", "Install uv"),
    ]
    assert not doctor.report(checks)
    assert "Install uv" in capsys.readouterr().out
    assert doctor.report([checks[0]], as_json=True)
    assert '"ready": true' in capsys.readouterr().out
