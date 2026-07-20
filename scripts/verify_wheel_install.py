import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def verify() -> dict[str, str]:
    wheel = next(Path("release/packages").glob("eduwork_databridge-0.14.0-*.whl"))
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
                "assert eduwork_databridge.__version__ == '0.14.0'; "
                "assert app.version == '0.14.0'"
            ),
        ],
        check=True,
    )
    result = {
        "wheel": wheel.name,
        "python": "3.12",
        "dependency_install": "passed",
        "import_version": "0.14.0",
        "fastapi_app_version": "0.14.0",
        "status": "passed",
    }
    output = Path("release/packages/wheel-install-verification.json")
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
