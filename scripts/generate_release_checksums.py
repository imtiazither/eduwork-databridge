import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "release/SHA256SUMS"


def release_files() -> list[Path]:
    files = [path for path in (ROOT / "release").rglob("*") if path.is_file() and path != OUTPUT]
    files += [
        ROOT / "benchmark-baseline/small-v0.14.0.json",
        ROOT / "benchmark-baseline/budgets.json",
        ROOT / "docs/assets/eduwork-databridge-walkthrough.mp4",
        ROOT / "docs/assets/reviewer-console.svg",
        ROOT / "docs/assets/lineage-view.svg",
    ]
    return sorted(set(files), key=lambda path: str(path.relative_to(ROOT)))


def render() -> str:
    lines = []
    for path in release_files():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(ROOT)}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != expected:
            raise SystemExit("Release checksums are out of date")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(expected, encoding="utf-8")
