import json
import os
import sqlite3
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def verify(output: Path) -> dict[str, object]:
    temporary = Path(tempfile.mkdtemp(prefix="eduwork-backup-restore-"))
    source = temporary / "source.db"
    restored = temporary / "restored.db"
    url = f"sqlite+pysqlite:///{source}"
    os.environ["EDUWORK_DATABASE_URL"] = url
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO organizations (name, organization_type, status, metadata_json, id) "
                "VALUES ('Backup Test', 'employer', 'active', '{}', :id)"
            ),
            {"id": "00000000000000000000000000000001"},
        )
    with sqlite3.connect(source) as source_connection, sqlite3.connect(restored) as target:
        source_connection.backup(target)
    restored_engine = create_engine(f"sqlite+pysqlite:///{restored}")
    source_tables = set(inspect(engine).get_table_names())
    restored_tables = set(inspect(restored_engine).get_table_names())
    with restored_engine.connect() as connection:
        organization_count = connection.scalar(text("SELECT COUNT(*) FROM organizations"))
        revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
    if source_tables != restored_tables or organization_count != 1:
        raise SystemExit("Backup/restore verification failed")
    result: dict[str, object] = {
        "status": "passed",
        "database": "sqlite reference verification",
        "table_count": len(restored_tables),
        "organization_count": organization_count,
        "alembic_revision": revision,
        "limitations": "Repeat with target PostgreSQL backup tooling before deployment.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    verify(Path("release/backup-restore-verification.json"))
