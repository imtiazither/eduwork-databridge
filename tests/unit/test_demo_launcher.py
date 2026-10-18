import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from scripts import demo
from scripts.demo_workspace import DemoWorkspace


def test_automatic_ports_skip_occupied_and_explicit_ports_fail():
    with demo.socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        assert demo.choose_port(port, None) != port
        with pytest.raises(ValueError, match="occupied"):
            demo.choose_port(port, port)
    with pytest.raises(ValueError):
        demo.choose_port(5173, 80)
    with pytest.raises(ValueError):
        demo.choose_port(5173, 5173, excluded=5173)


def test_reset_requires_explicit_confirmation(monkeypatch):
    monkeypatch.setattr(demo.sys.stdin, "isatty", lambda: False)
    with pytest.raises(ValueError, match="confirmation"):
        demo.confirm_reset("quickstart", False)
    demo.confirm_reset("quickstart", True)
    monkeypatch.setattr(demo.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: "no")
    with pytest.raises(ValueError, match="cancelled"):
        demo.confirm_reset("quickstart", False)
    monkeypatch.setattr("builtins.input", lambda prompt: "RESET quickstart")
    demo.confirm_reset("quickstart", False)


def test_preparation_seeds_once_and_keeps_saved_history(monkeypatch, tmp_path: Path):
    workspace = DemoWorkspace(tmp_path)
    python = tmp_path / ".venv" / ("Scripts/python.exe" if demo.os.name == "nt" else "bin/python")
    vite = tmp_path / "apps/reviewer-ui/node_modules/vite/bin/vite.js"
    fixture = tmp_path / "data/synthetic/small/dataset_manifest.json"
    for file in [python, vite, fixture]:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("{}")
    step = Mock()
    monkeypatch.setattr(demo, "run_step", step)
    with workspace.locked():
        workspace.initialize()
        demo.prepare(workspace, True)
        assert any("scripts/run_demo.py" in call.args[1] for call in step.call_args_list)
        (workspace.path / "control.db").write_text("saved review")
        step.reset_mock()
        demo.prepare(workspace, True)
        assert not any("scripts/run_demo.py" in call.args[1] for call in step.call_args_list)
        assert (workspace.path / "control.db").read_text() == "saved review"


def test_missing_dependencies_are_actionable(tmp_path: Path):
    workspace = DemoWorkspace(tmp_path)
    with workspace.locked():
        workspace.initialize()
        with pytest.raises(ValueError, match="without --skip-install"):
            demo.prepare(workspace, True)


def test_readiness_checks_version_database_identity_and_seeded_queue(monkeypatch):
    read = Mock(
        side_effect=[{"version": "0.61.0"}, {"status": "ready"}, [{"id": "org"}], {"total": 9}]
    )
    monkeypatch.setattr(demo, "read_json", read)
    demo.verify_ready("http://127.0.0.1:5173", "0.61.0")
    assert read.call_args.args[2]["X-Organization-ID"] == "org"
    read.side_effect = [{"version": "old"}]
    with pytest.raises(ValueError, match="unexpected version"):
        demo.verify_ready("http://127.0.0.1:5173", "0.61.0")


def test_startup_fails_if_server_exits_or_times_out(monkeypatch):
    exited = Mock(poll=Mock(return_value=1))
    with pytest.raises(ValueError, match="exited"):
        demo.wait_ready("http://127.0.0.1:5173", "0.61.0", [exited])
    with pytest.raises(ValueError, match="in time"):
        demo.wait_ready("http://127.0.0.1:5173", "0.61.0", [], timeout=0)


def test_stop_reaps_server_processes(monkeypatch):
    monkeypatch.setattr(demo.os, "killpg", Mock())
    child = Mock(pid=999999, poll=Mock(return_value=None))
    child.wait.side_effect = [subprocess.TimeoutExpired("server", 8), 0]
    demo.stop([child])
    assert child.wait.call_count == 2


def test_prepare_only_releases_lock_and_unconfirmed_reset_preserves_data(
    monkeypatch, tmp_path: Path
):
    monkeypatch.setattr(demo, "ROOT", tmp_path)
    monkeypatch.setattr(demo, "report", lambda checks: True)
    monkeypatch.setattr(demo, "inspect", lambda **kwargs: [])
    monkeypatch.setattr(demo, "prepare", lambda workspace, skip: tmp_path / "python")
    assert demo.main(["--prepare-only"]) == 0
    workspace = DemoWorkspace(tmp_path)
    data = workspace.path / "control.db"
    data.write_text("keep")
    monkeypatch.setattr(demo.sys.stdin, "isatty", lambda: False)
    assert demo.main(["--reset", "--prepare-only"]) == 1
    assert data.read_text() == "keep"
    assert not (workspace.path.parent / ".quickstart.lock").exists()


def test_failed_readiness_stops_every_started_server(monkeypatch, tmp_path: Path):
    workspace = DemoWorkspace(tmp_path)
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.61.0"\n')
    children = [Mock(), Mock()]
    monkeypatch.setattr(demo.subprocess, "Popen", Mock(side_effect=children))
    monkeypatch.setattr(demo, "wait_ready", Mock(side_effect=ValueError("not ready")))
    stop = Mock()
    monkeypatch.setattr(demo, "stop", stop)
    with workspace.locked():
        workspace.initialize()
        with pytest.raises(ValueError, match="not ready"):
            demo.serve(workspace, tmp_path / "python", 8000, 5173, False)
    stop.assert_called_once_with(children)
