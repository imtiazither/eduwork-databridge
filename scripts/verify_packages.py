import hashlib
import json
import tarfile
import tomllib
import zipfile
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project_version() -> str:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    return str(project["project"]["version"])


def verify(directory: Path, output: Path) -> None:
    version = project_version()
    wheels = sorted(directory.glob(f"eduwork_databridge-{version}-*.whl"))
    sdists = sorted(directory.glob(f"eduwork_databridge-{version}.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise SystemExit(f"Expected one v{version} wheel and one source distribution")
    wheel, sdist = wheels[0], sdists[0]
    distribution = f"eduwork_databridge-{version}.dist-info"
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        required_wheel = {
            "eduwork_databridge/__init__.py",
            "eduwork_databridge/main.py",
            f"{distribution}/METADATA",
            f"{distribution}/licenses/LICENSE",
        }
        if not required_wheel <= names:
            raise SystemExit("Wheel is missing required files")
        metadata = archive.read(f"{distribution}/METADATA").decode()
        if f"Version: {version}" not in metadata or "Requires-Python: <3.14,>=3.12" not in metadata:
            raise SystemExit("Wheel metadata version or Python range is invalid")
    with tarfile.open(sdist, "r:gz") as archive:
        names = set(archive.getnames())
        prefix = f"eduwork_databridge-{version}/"
        required_sdist = {
            prefix + "pyproject.toml",
            prefix + "README.md",
            prefix + "LICENSE",
            prefix + "packages/eduwork_databridge/eduwork_databridge/main.py",
        }
        if not required_sdist <= names:
            raise SystemExit("Source distribution is missing required files")
    result = {
        "version": version,
        "wheel": {"name": wheel.name, "bytes": wheel.stat().st_size, "sha256": sha256(wheel)},
        "sdist": {"name": sdist.name, "bytes": sdist.stat().st_size, "sha256": sha256(sdist)},
        "status": "passed",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    verify(Path("release/packages"), Path("release/packages/package-verification.json"))
