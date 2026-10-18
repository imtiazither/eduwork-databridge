"""Owned, isolated storage for synthetic demos; never uses the application's database URL."""

import hashlib
import json
import os
import re
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

MARKER = {"kind": "eduwork-synthetic-demo", "format": 1}


class DemoWorkspace:
    def __init__(self, root: Path, name: str = "quickstart") -> None:
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", name):
            raise ValueError("Workspace names must be 1-40 lowercase letters, digits, or hyphens.")
        self.root = root.resolve()
        self.name = name
        self._locked = False

    @property
    def path(self) -> Path:
        path = self.root
        for component in ("var", "demos", self.name):
            path = path / component
            if path.is_symlink() or (path.exists() and not path.is_dir()):
                raise ValueError(f"Refusing unsafe demo path: {path}")
        return path

    def _require_lock(self) -> None:
        if not self._locked:
            raise ValueError("Acquire the demo workspace lock before modifying demo data.")

    def _verify_owner(self) -> None:
        marker = self.path / ".eduwork-demo.json"
        try:
            valid = not marker.is_symlink() and json.loads(marker.read_text()) == MARKER
        except (OSError, ValueError):
            valid = False
        if not valid:
            raise ValueError(
                f"Not an owned synthetic demo workspace; leaving it untouched: {self.path}"
            )
        if any(child.is_symlink() for child in self.path.rglob("*")):
            raise ValueError("Refusing symbolic links inside the synthetic demo workspace.")

    @contextmanager
    def locked(self) -> Iterator[None]:
        parent = self.path.parent
        parent.mkdir(parents=True, exist_ok=True)
        lock = parent / f".{self.name}.lock"
        try:
            descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise ValueError(
                f"Demo workspace is already in use. Stop its launcher first. "
                f"After an interrupted session, remove {lock} "
                "only after checking no demo is running."
            ) from exc
        try:
            with os.fdopen(descriptor, "w") as stream:
                stream.write(str(os.getpid()))
            self._locked = True
            yield
        finally:
            self._locked = False
            lock.unlink()

    def initialize(self) -> None:
        self._require_lock()
        if self.path.exists():
            self._verify_owner()
        else:
            self.path.mkdir(mode=0o700)
            (self.path / ".eduwork-demo.json").write_text(json.dumps(MARKER) + "\n")
        for directory in ("raw", "marts", "exports", "lineage", "logs"):
            (self.path / directory).mkdir(exist_ok=True)

    def reset(self) -> None:
        self._require_lock()
        if self.path.exists():
            self._verify_owner()
            shutil.rmtree(self.path)
        self.initialize()

    def fixture_hash(self) -> str:
        manifest = self.root / "data/synthetic/small/dataset_manifest.json"
        return hashlib.sha256(manifest.read_bytes()).hexdigest()

    def prepared(self) -> bool:
        stamp = self.path / "prepared.json"
        if not stamp.exists():
            return False
        if json.loads(stamp.read_text()).get("fixture_sha256") != self.fixture_hash():
            raise ValueError("Synthetic fixtures changed. Use --reset to prepare a fresh demo.")
        return (self.path / "control.db").is_file()

    def mark_prepared(self) -> None:
        self._require_lock()
        (self.path / "prepared.json").write_text(
            json.dumps({"fixture_sha256": self.fixture_hash()}) + "\n"
        )

    def environment(self) -> dict[str, str]:
        database = (self.path / "control.db").as_posix()
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("EDUWORK_", "VITE_"))
        }
        env.update(
            {
                "EDUWORK_DATABASE_URL": f"sqlite+pysqlite:///{database}",
                "EDUWORK_ENVIRONMENT": "development",
                "EDUWORK_DEMO_MODE": "true",
                "EDUWORK_DEMO_IDENTITY_ENABLED": "true",
                "EDUWORK_ALLOW_PRIVATE_NETWORK_SOURCES": "false",
                "EDUWORK_ALLOWED_FILE_ROOTS": json.dumps([str(self.root / "data/synthetic")]),
                "EDUWORK_RAW_STORE_ROOT": str(self.path / "raw"),
                "EDUWORK_MART_ROOT": str(self.path / "marts"),
                "EDUWORK_EXPORT_ROOT": str(self.path / "exports"),
                "EDUWORK_LINEAGE_ROOT": str(self.path / "lineage"),
                "EDUWORK_TELEMETRY_ENABLED": "false",
                "EDUWORK_RATE_LIMIT_PER_MINUTE": "1000",
                "VITE_API_BASE_URL": "",
                "PYTHONUNBUFFERED": "1",
            }
        )
        return env
