import hashlib
import json
import tarfile
import zipfile
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(directory: Path, output: Path) -> None:
    wheels = sorted(directory.glob("eduwork_databridge-0.15.0-*.whl"))
    sdists = sorted(directory.glob("eduwork_databridge-0.15.0.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise SystemExit("Expected one v0.15.0 wheel and one source distribution")
    wheel, sdist = wheels[0], sdists[0]
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        required_wheel = {
            "eduwork_databridge/__init__.py",
            "eduwork_databridge/main.py",
            "eduwork_databridge-0.15.0.dist-info/METADATA",
            "eduwork_databridge-0.15.0.dist-info/licenses/LICENSE",
        }
        if not required_wheel <= names:
            raise SystemExit("Wheel is missing required files")
        metadata = archive.read("eduwork_databridge-0.15.0.dist-info/METADATA").decode()
        if "Version: 0.15.0" not in metadata or "Requires-Python: <3.14,>=3.12" not in metadata:
            raise SystemExit("Wheel metadata version or Python range is invalid")
    with tarfile.open(sdist, "r:gz") as archive:
        names = set(archive.getnames())
        prefix = "eduwork_databridge-0.15.0/"
        required_sdist = {
            prefix + "pyproject.toml",
            prefix + "README.md",
            prefix + "LICENSE",
            prefix + "packages/eduwork_databridge/eduwork_databridge/main.py",
        }
        if not required_sdist <= names:
            raise SystemExit("Source distribution is missing required files")
    result = {
        "version": "0.15.0",
        "wheel": {"name": wheel.name, "bytes": wheel.stat().st_size, "sha256": sha256(wheel)},
        "sdist": {"name": sdist.name, "bytes": sdist.stat().st_size, "sha256": sha256(sdist)},
        "status": "passed",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    verify(Path("release/packages"), Path("release/packages/package-verification.json"))
