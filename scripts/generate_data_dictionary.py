import argparse
from pathlib import Path

from eduwork_databridge.db import Base, models  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/reference/data-dictionary.md"


def render() -> str:
    lines = [
        "# Data Dictionary",
        "",
        "Generated from SQLAlchemy metadata. Do not edit by hand.",
        "",
    ]
    for table in sorted(Base.metadata.tables.values(), key=lambda value: value.name):
        lines += [
            f"## {table.name}",
            "",
            "| Column | Type | Nullable | Key/Reference |",
            "|---|---|---:|---|",
        ]
        for column in table.columns:
            key = "PK" if column.primary_key else ""
            if column.foreign_keys:
                ref = next(iter(column.foreign_keys)).target_fullname
                key = f"{key} FK → {ref}".strip()
            lines.append(
                f"| {column.name} | {column.type} | {'yes' if column.nullable else 'no'} | {key} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main(check: bool = False) -> None:
    expected = render()
    if check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != expected:
            raise SystemExit("Generated data dictionary is out of date")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(expected, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    main(parser.parse_args().check)
