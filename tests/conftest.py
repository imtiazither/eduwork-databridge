import os

import pytest

os.environ.setdefault("EDUWORK_DATABASE_URL", "sqlite+pysqlite:///:memory:")


@pytest.fixture(scope="session", autouse=True)
def dispose_application_engine():
    """Close the shared test engine instead of leaving SQLite resources to GC."""
    yield
    from eduwork_databridge.db.session import engine

    engine.dispose()
