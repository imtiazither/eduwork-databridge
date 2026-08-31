import json
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path


def verify() -> dict[str, str]:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    version = str(project["project"]["version"])
    wheel = next(Path("release/packages").glob(f"eduwork_databridge-{version}-*.whl"))
    uv = shutil.which("uv")
    if uv is None:
        fallback = Path.home() / ".local/bin/uv"
        uv = str(fallback) if fallback.exists() else None
    if uv is None:
        raise SystemExit("uv is unavailable")
    environment = Path(tempfile.mkdtemp(prefix="eduwork-wheel-"))
    subprocess.run([uv, "venv", str(environment), "--python", "3.12"], check=True)
    python = environment / "bin/python"
    subprocess.run(
        [uv, "pip", "install", "--python", str(python), str(wheel)],
        check=True,
    )
    subprocess.run(
        [
            str(python),
            "-c",
            (
                "import eduwork_databridge; "
                "from eduwork_databridge.main import app; "
                f"assert eduwork_databridge.__version__ == {version!r}; "
                f"assert app.version == {version!r}"
            ),
        ],
        check=True,
    )
    result = {
        "wheel": wheel.name,
        "python": "3.12",
        "dependency_install": "passed",
        "import_version": version,
        "fastapi_app_version": version,
        "status": "passed",
    }
    output = Path("release/packages/wheel-install-verification.json")
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
