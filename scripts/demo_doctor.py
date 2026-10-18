"""Read-only prerequisite checks for the local synthetic demo (standard library only)."""

import argparse
import json
import re
import shutil
import socket
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    remedy: str = ""


def tool_version(name: str, minimum: tuple[int, ...]) -> Check:
    executable = shutil.which(name)
    remedy = {
        "uv": "Install uv: https://docs.astral.sh/uv/getting-started/installation/",
        "node": "Install Node.js 24 LTS (includes npm): https://nodejs.org/en/download",
        "npm": "Reinstall Node.js 24 LTS, then reopen your terminal.",
    }[name]
    if executable is None:
        return Check(name, False, "Not found on PATH", remedy)
    try:
        result = subprocess.run(
            [executable, "--version"], capture_output=True, text=True, timeout=15, check=True
        )
        match = re.search(r"(\d+)\.(\d+)\.(\d+)", result.stdout)
        version = tuple(map(int, match.groups())) if match else ()
        supported = version >= minimum
        if name == "node":
            supported = supported and version[0] in {24, 26}
        return Check(name, supported, result.stdout.strip(), "" if supported else remedy)
    except (OSError, subprocess.SubprocessError) as exc:
        return Check(name, False, f"Could not run {name}: {type(exc).__name__}", remedy)


def port_check(name: str, port: int) -> Check:
    if not 1024 <= port <= 65535:
        return Check(name, False, f"Invalid port {port}", "Choose a port from 1024 to 65535.")
    try:
        with socket.socket() as probe:
            if sys.platform != "win32":
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", port))
            probe.listen(1)
        return Check(name, True, f"127.0.0.1:{port} is available")
    except OSError:
        return Check(
            name,
            False,
            f"127.0.0.1:{port} is occupied",
            "Choose another --api-port or --ui-port. The launcher selects free ports by default.",
        )


def inspect(root: Path = ROOT, api_port: int = 8000, ui_port: int = 5173) -> list[Check]:
    python_ok = (3, 12) <= sys.version_info[:2] < (3, 14)
    checks = [
        Check(
            "Python",
            python_ok,
            sys.version.split()[0],
            "" if python_ok else "Install Python 3.12 or 3.13: https://www.python.org/downloads/",
        ),
        tool_version("uv", (0, 11, 29)),
        tool_version("node", (24, 0, 0)),
        tool_version("npm", (10, 0, 0)),
    ]
    required = [
        "uv.lock",
        "apps/reviewer-ui/package-lock.json",
        "data/synthetic/small/dataset_manifest.json",
    ]
    missing = [path for path in required if not (root / path).is_file()]
    checks.append(
        Check(
            "Project files",
            not missing,
            ", ".join(missing) if missing else "Demo files are present",
            "Download or clone the complete repository, then run this command from its folder."
            if missing
            else "",
        )
    )
    checks.extend([port_check("API port", api_port), port_check("UI port", ui_port)])
    if api_port == ui_port:
        checks.append(
            Check(
                "Separate ports",
                False,
                "API and UI ports are identical",
                "Choose two different ports.",
            )
        )
    return checks


def report(checks: list[Check], as_json: bool = False) -> bool:
    passed = all(check.ok for check in checks)
    if as_json:
        print(
            json.dumps({"ready": passed, "checks": [asdict(check) for check in checks]}, indent=2)
        )
    else:
        for check in checks:
            print(f"[{'OK' if check.ok else 'FIX'}] {check.name}: {check.detail}")
            if check.remedy:
                print(f"      {check.remedy}")
        print(
            "Ready to start the synthetic demo."
            if passed
            else "Fix the items above, then run the checker again."
        )
    return passed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print a machine-readable report")
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--ui-port", type=int, default=5173)
    args = parser.parse_args()
    return 0 if report(inspect(api_port=args.api_port, ui_port=args.ui_port), args.json) else 1


if __name__ == "__main__":
    raise SystemExit(main())
