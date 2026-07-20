import argparse
import json
import re
from pathlib import Path

PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
    "openai_style_key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "google_api_key": re.compile(r"AIza[0-9A-Za-z_-]{35}"),
}
TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".ini",
    ".txt",
    ".tsx",
    ".ts",
    ".js",
    ".css",
    ".html",
    ".mako",
    ".env",
    ".example",
    ".dockerignore",
    ".gitignore",
}
EXCLUDED_PARTS = {".venv", "node_modules", "dist", "site", "var", "__pycache__"}


def scan(root: Path) -> list[dict[str, str | int]]:
    findings: list[dict[str, str | int]] = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {
            "Dockerfile",
            "Makefile",
            "LICENSE",
            "NOTICE",
        }:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern_name, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.append(
                        {
                            "file": str(path.relative_to(root)),
                            "line": line_number,
                            "pattern": pattern_name,
                        }
                    )
    return findings


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    findings = scan(args.root.resolve())
    result = {"scanner": "eduwork-targeted-secret-scan", "findings": findings}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if findings:
        raise SystemExit(f"Potential secrets found: {len(findings)}")
    print("Targeted secret scan passed: 0 findings")
