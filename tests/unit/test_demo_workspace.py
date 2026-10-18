import json
from pathlib import Path

import pytest

from scripts.demo_workspace import DemoWorkspace


def test_isolated_environment_ignores_external_database_and_roots(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("EDUWORK_DATABASE_URL", "postgresql://company-database")
    monkeypatch.setenv("EDUWORK_RAW_STORE_ROOT", "/company/data")
    monkeypatch.setenv("VITE_API_BASE_URL", "https://company.example")
    workspace = DemoWorkspace(tmp_path)
    env = workspace.environment()
    assert env["EDUWORK_DATABASE_URL"].endswith("/var/demos/quickstart/control.db")
    assert env["EDUWORK_RAW_STORE_ROOT"] == str(workspace.path / "raw")
    assert env["VITE_API_BASE_URL"] == ""
    assert env["EDUWORK_DEMO_IDENTITY_ENABLED"] == "true"


def test_reset_only_deletes_owned_demo_data(tmp_path: Path):
    original = tmp_path / "existing.db"
    original.write_text("keep")
    workspace = DemoWorkspace(tmp_path)
    with workspace.locked():
        workspace.initialize()
        (workspace.path / "control.db").write_text("demo only")
        workspace.reset()
        assert not (workspace.path / "control.db").exists()
        assert (workspace.path / ".eduwork-demo.json").exists()
    assert original.read_text() == "keep"
    assert not (workspace.path.parent / ".quickstart.lock").exists()


def test_unowned_directory_and_symlink_are_never_removed(tmp_path: Path):
    workspace = DemoWorkspace(tmp_path)
    workspace.path.mkdir(parents=True)
    keep = workspace.path / "keep.txt"
    keep.write_text("keep")
    with workspace.locked(), pytest.raises(ValueError, match="Not an owned"):
        workspace.reset()
    assert keep.exists()
    other = tmp_path / "other"
    other.mkdir()
    workspace.path.rename(tmp_path / "preserved")
    workspace.path.symlink_to(other, target_is_directory=True)
    with pytest.raises(ValueError, match="unsafe"):
        workspace.environment()


@pytest.mark.parametrize("name", ["../company", "", "/tmp/data", "a/b", "UPPER", "a" * 41])
def test_workspace_name_cannot_escape_owned_root(tmp_path: Path, name: str):
    with pytest.raises(ValueError):
        DemoWorkspace(tmp_path, name)


def test_live_workspace_cannot_be_reset_by_another_launcher(tmp_path: Path):
    first = DemoWorkspace(tmp_path)
    with first.locked():
        first.initialize()
        with pytest.raises(ValueError, match="already in use"), DemoWorkspace(tmp_path).locked():
            pytest.fail("Second lock should not be acquired")
    with pytest.raises(ValueError, match="lock"):
        first.reset()


def test_preparation_stamp_reuses_data_and_detects_changed_fixture(tmp_path: Path):
    fixture = tmp_path / "data/synthetic/small/dataset_manifest.json"
    fixture.parent.mkdir(parents=True)
    fixture.write_text(json.dumps({"synthetic": True}))
    workspace = DemoWorkspace(tmp_path)
    with workspace.locked():
        workspace.initialize()
        assert not workspace.prepared()
        (workspace.path / "control.db").touch()
        workspace.mark_prepared()
        assert workspace.prepared()
        fixture.write_text("changed")
        with pytest.raises(ValueError, match="fixtures changed"):
            workspace.prepared()


def test_database_symlink_is_refused_before_use(tmp_path: Path):
    workspace = DemoWorkspace(tmp_path)
    company = tmp_path / "company.db"
    company.write_text("private database")
    with workspace.locked():
        workspace.initialize()
        (workspace.path / "control.db").symlink_to(company)
        with pytest.raises(ValueError, match="symbolic links"):
            workspace.initialize()
    assert company.read_text() == "private database"
