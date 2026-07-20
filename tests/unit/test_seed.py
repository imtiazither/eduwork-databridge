from eduwork_databridge import seed as seed_module
from eduwork_databridge.db import Base
from eduwork_databridge.db.models.control import SourceSystem
from eduwork_databridge.db.models.core import Organization
from eduwork_databridge.db.models.security import Permission, Role, RolePermission
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker


def test_seed_is_idempotent(monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    monkeypatch.setattr(seed_module, "SessionLocal", session_factory)

    seed_module.seed()
    seed_module.seed()

    with session_factory() as session:
        organization_count = session.scalar(select(func.count()).select_from(Organization))
        source_count = session.scalar(select(func.count()).select_from(SourceSystem))
        permission_count = session.scalar(select(func.count()).select_from(Permission))
        role_count = session.scalar(select(func.count()).select_from(Role))
        role_permission_count = session.scalar(select(func.count()).select_from(RolePermission))
        assert organization_count == 1
        assert source_count == 6
        assert permission_count == len(seed_module.PERMISSIONS)
        assert role_count == len(seed_module.ROLE_PERMISSIONS)
        assert role_permission_count == sum(
            len(values) for values in seed_module.ROLE_PERMISSIONS.values()
        )
