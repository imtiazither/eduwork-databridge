import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from eduwork_databridge.db.models.control import DataContract, SourceObject, SourceSystem
from eduwork_databridge.db.models.core import Organization
from eduwork_databridge.db.models.security import Permission, Role, RolePermission
from eduwork_databridge.db.session import SessionLocal

SEED_PATH = Path("configs/demo/seed_metadata.json")
PERMISSIONS = {
    "sources:read": "Read source metadata",
    "ingestion:write": "Run immutable extraction",
    "profiles:write": "Create profiles and drift comparisons",
    "mappings:write": "Execute mapping previews",
    "validation:write": "Execute validation and resolve quarantine",
    "matching:write": "Execute identity matching and review decisions",
    "marts:write": "Build governed marts",
    "exports:write": "Publish documented exports",
    "lineage:read": "Read lineage traces",
    "audit:read": "Read organization audit events",
    "retention:write": "Manage and apply retention policies",
}
ROLE_PERMISSIONS = {
    "administrator": set(PERMISSIONS),
    "data_steward": {
        "sources:read",
        "ingestion:write",
        "profiles:write",
        "mappings:write",
        "validation:write",
        "matching:write",
        "lineage:read",
    },
    "publisher": {"marts:write", "exports:write", "lineage:read"},
    "viewer": {"sources:read", "lineage:read"},
}


def _seed_security(session: Session) -> None:
    permission_rows: dict[str, Permission] = {}
    for key, description in PERMISSIONS.items():
        row = session.scalar(select(Permission).where(Permission.permission_key == key))
        if row is None:
            row = Permission(permission_key=key, description=description)
            session.add(row)
            session.flush()
        permission_rows[key] = row
    for role_key, permission_keys in ROLE_PERMISSIONS.items():
        role = session.scalar(select(Role).where(Role.role_key == role_key))
        if role is None:
            role = Role(role_key=role_key, name=role_key.replace("_", " ").title())
            session.add(role)
            session.flush()
        for permission_key in permission_keys:
            exists = session.scalar(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == permission_rows[permission_key].id,
                )
            )
            if exists is None:
                session.add(
                    RolePermission(
                        role_id=role.id,
                        permission_id=permission_rows[permission_key].id,
                    )
                )


def seed() -> None:
    data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    with SessionLocal() as session:
        organization = session.scalar(
            select(Organization).where(Organization.name == data["organization"]["name"])
        )
        if organization is None:
            organization = Organization(**data["organization"])
            session.add(organization)
            session.flush()
        for source_spec in data["sources"]:
            source_values = source_spec["source"]
            source = session.scalar(
                select(SourceSystem).where(
                    SourceSystem.organization_id == organization.id,
                    SourceSystem.source_key == source_values["source_key"],
                )
            )
            if source is None:
                source = SourceSystem(organization_id=organization.id, **source_values)
                session.add(source)
                session.flush()
            for object_spec in source_spec["objects"]:
                object_values = object_spec["object"]
                source_object = session.scalar(
                    select(SourceObject).where(
                        SourceObject.source_system_id == source.id,
                        SourceObject.object_key == object_values["object_key"],
                    )
                )
                if source_object is None:
                    source_object = SourceObject(source_system_id=source.id, **object_values)
                    session.add(source_object)
                    session.flush()
                contract_values = object_spec["contract"]
                contract = session.scalar(
                    select(DataContract).where(
                        DataContract.source_object_id == source_object.id,
                        DataContract.contract_key == contract_values["contract_key"],
                        DataContract.version == contract_values["version"],
                    )
                )
                if contract is None:
                    session.add(DataContract(source_object_id=source_object.id, **contract_values))
        _seed_security(session)
        session.commit()


if __name__ == "__main__":
    seed()
