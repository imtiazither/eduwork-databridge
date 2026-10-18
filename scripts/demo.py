"""Start a private, synthetic DataBridge demo with one command."""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import webbrowser
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from urllib.error import URLError
from urllib.request import ProxyHandler, Request, build_opener

if TYPE_CHECKING or not __package__:
    from demo_doctor import ROOT, inspect, port_check, report
    from demo_workspace import DemoWorkspace
else:
    from scripts.demo_doctor import ROOT, inspect, port_check, report
    from scripts.demo_workspace import DemoWorkspace


def choose_port(preferred: int, explicit: int | None, excluded: int | None = None) -> int:
    candidates = [explicit] if explicit is not None else list(range(preferred, preferred + 50))
    for port in candidates:
        if port == excluded or not 1024 <= port <= 65535:
            continue
        if port_check("Demo port", port).ok:
            return port
    raise ValueError(
        "The requested port is occupied or invalid. Choose another --api-port or --ui-port."
    )


def confirm_reset(name: str, yes: bool) -> None:
    if yes:
        return
    if not sys.stdin.isatty():
        raise ValueError("Reset needs confirmation. For automation, explicitly pass --reset --yes.")
    expected = f"RESET {name}"
    answer = input(f"Delete only this synthetic demo's data and notes? Type '{expected}': ")
    if answer != expected:
        raise ValueError("Reset cancelled. Existing demo data was not changed.")


def run_step(label: str, command: list[str], root: Path, env: dict[str, str], log: Path) -> None:
    print(label, flush=True)
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"\n{label}\n")
        stream.flush()
        child = subprocess.Popen(
            command,
            cwd=root,
            env=env,
            stdout=stream,
            stderr=stream,
            start_new_session=os.name == "posix",
        )
        try:
            code = child.wait()
        except BaseException:
            stop([child])
            raise
        if code:
            raise subprocess.CalledProcessError(code, command)


def prepare(workspace: DemoWorkspace, skip_install: bool) -> Path:
    env = workspace.environment()
    root = workspace.root
    python = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    vite = root / "apps/reviewer-ui/node_modules/vite/bin/vite.js"
    log = workspace.path / "logs/setup.log"
    if not skip_install:
        run_step(
            "Installing locked Python dependencies (first run may take a few minutes)...",
            [cast(str, shutil.which("uv")), "sync", "--frozen", "--extra", "dev"],
            root,
            env,
            log,
        )
        run_step(
            "Installing locked reviewer dependencies...",
            [cast(str, shutil.which("npm")), "--prefix", "apps/reviewer-ui", "ci"],
            root,
            env,
            log,
        )
    if not python.is_file() or not vite.is_file():
        raise ValueError("Dependencies are missing. Run again without --skip-install.")
    prepared = workspace.prepared()
    if not prepared and (workspace.path / "control.db").exists():
        raise ValueError("An earlier demo setup was interrupted. Use --reset to prepare it again.")
    run_step(
        "Applying database upgrades...",
        [str(python), "-m", "alembic", "upgrade", "head"],
        root,
        env,
        log,
    )
    run_step(
        "Preparing synthetic source metadata...",
        [str(python), "-m", "eduwork_databridge.seed"],
        root,
        env,
        log,
    )
    if not prepared:
        run_step(
            "Loading fictional records and review queues...",
            [str(python), "scripts/run_demo.py"],
            root,
            env,
            log,
        )
        workspace.mark_prepared()
    else:
        print("Reusing saved synthetic records and review history.", flush=True)
    return python


def read_json(base: str, path: str, headers: dict[str, str] | None = None) -> Any:
    request = Request(f"{base}{path}", headers=headers or {})
    with build_opener(ProxyHandler({})).open(request, timeout=3) as response:
        return json.load(response)


def verify_ready(base: str, version: str) -> None:
    if read_json(base, "/healthz").get("version") != version:
        raise ValueError("The demo API reported an unexpected version.")
    if read_json(base, "/readyz").get("status") != "ready":
        raise ValueError("The demo database is not ready.")
    headers = {"X-Demo-User": "demo-admin"}
    organizations = read_json(base, "/api/v1/organizations", headers)
    if not organizations:
        raise ValueError("Synthetic organization was not prepared.")
    headers["X-Organization-ID"] = organizations[0]["id"]
    summary = read_json(base, "/api/v1/quarantine/summary", headers)
    if summary.get("total", 0) < 1:
        raise ValueError("Synthetic exception queue was not prepared.")


def wait_ready(
    base: str, version: str, children: Sequence[subprocess.Popen[bytes]], timeout: float = 90
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if any(child.poll() is not None for child in children):
            raise ValueError("A demo server exited. See the api.log and ui.log files.")
        try:
            verify_ready(base, version)
            return
        except (OSError, URLError, ValueError, KeyError):
            time.sleep(0.4)
    raise ValueError("The demo did not become ready in time. See the api.log and ui.log files.")


def stop(children: Sequence[subprocess.Popen[bytes]]) -> None:
    for child in reversed(children):
        if child.poll() is not None:
            continue
        try:
            if os.name == "posix":
                os.killpg(child.pid, signal.SIGTERM)
            else:
                child.terminate()
            child.wait(timeout=8)
        except ProcessLookupError:
            pass
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                os.killpg(child.pid, signal.SIGKILL)
            else:
                child.kill()
            child.wait()


def serve(
    workspace: DemoWorkspace, python: Path, api_port: int, ui_port: int, open_browser: bool
) -> None:
    import tomllib

    root = workspace.root
    env = workspace.environment()
    env["VITE_DEMO_PROXY_TARGET"] = f"http://127.0.0.1:{api_port}"
    version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    commands = [
        (
            "api",
            [
                str(python),
                "-m",
                "uvicorn",
                "eduwork_databridge.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(api_port),
            ],
        ),
        (
            "ui",
            [
                cast(str, shutil.which("node")),
                str(root / "apps/reviewer-ui/node_modules/vite/bin/vite.js"),
                "--host",
                "127.0.0.1",
                "--port",
                str(ui_port),
                "--strictPort",
            ],
        ),
    ]
    children: list[subprocess.Popen[bytes]] = []
    try:
        for name, command in commands:
            with (workspace.path / f"logs/{name}.log").open("ab") as log:
                children.append(
                    subprocess.Popen(
                        command,
                        cwd=root / "apps/reviewer-ui" if name == "ui" else root,
                        env=env,
                        stdout=log,
                        stderr=log,
                        start_new_session=os.name == "posix",
                    )
                )
        base = f"http://127.0.0.1:{ui_port}"
        wait_ready(base, version, children)
        url = f"{base}/#workspace"
        print(
            f"\nEduWork DataBridge v{version} is ready.\nOpen: {url}\n"
            f"Synthetic data and logs: {workspace.path}\n"
            "Choose Exceptions, save a resolution note, then reload to see its history.\n"
            "Keep this terminal open. Press Ctrl+C to stop both demo servers.\n",
            flush=True,
        )
        if open_browser:
            try:
                webbrowser.open(url)
            except webbrowser.Error:
                print("Browser could not open automatically. Use the link above.", flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(0.5)
        raise ValueError("A demo server stopped unexpectedly. Check the workspace logs.")
    finally:
        stop(children)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default="quickstart", help="Named synthetic workspace")
    parser.add_argument("--api-port", type=int)
    parser.add_argument("--ui-port", type=int)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument(
        "--skip-install", action="store_true", help="Reuse already installed locked dependencies"
    )
    parser.add_argument(
        "--prepare-only", action="store_true", help="Prepare data without starting servers"
    )
    parser.add_argument(
        "--reset", action="store_true", help="Reset only this owned synthetic workspace"
    )
    parser.add_argument(
        "--yes", action="store_true", help="Explicitly confirm --reset for automation"
    )
    args = parser.parse_args(argv)
    try:
        api_port = choose_port(8000, args.api_port)
        ui_port = choose_port(5173, args.ui_port, api_port)
        if not report(inspect(api_port=api_port, ui_port=ui_port)):
            return 1
        workspace = DemoWorkspace(ROOT, args.workspace)
        with workspace.locked():
            if args.reset:
                confirm_reset(args.workspace, args.yes)
                workspace.reset()
            else:
                workspace.initialize()
            python = prepare(workspace, args.skip_install)
            if args.prepare_only:
                print(f"Synthetic demo prepared: {workspace.path}", flush=True)
                return 0
            serve(workspace, python, api_port, ui_port, not args.no_browser)
    except KeyboardInterrupt:
        print("\nDemo stopped. Synthetic data and saved notes are kept for next time.", flush=True)
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(
            f"\nDemo could not start: {exc}\n"
            "See var/demos/<workspace>/logs/. Fix the cause and retry; "
            "use --reset only to discard this demo's synthetic data.",
            file=sys.stderr,
            flush=True,
        )
        return 1
    return 0


def interrupt(_signal: int, _frame: object) -> None:
    raise KeyboardInterrupt


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupt)
    raise SystemExit(main())
