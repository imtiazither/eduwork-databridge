import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from eduwork_databridge.connectors.base import ConnectorError
from eduwork_databridge.db.models.control import (
    ExportDefinition,
    ExportSnapshot,
    RetentionPolicy,
)
from eduwork_databridge.schemas.config import RetentionPolicyConfig


@dataclass(frozen=True)
class RetentionOutcome:
    candidate_ids: list[uuid.UUID]
    deleted_files: list[str]
    dry_run: bool


class RetentionService:
    def __init__(self, session: Session, export_root: Path = Path("var/exports")) -> None:
        self.session = session
        self.export_root = export_root.expanduser().resolve()

    def upsert_policy(
        self,
        organization_id: uuid.UUID,
        config: RetentionPolicyConfig,
    ) -> RetentionPolicy:
        policy = self.session.scalar(
            select(RetentionPolicy).where(
                RetentionPolicy.organization_id == organization_id,
                RetentionPolicy.policy_key == config.policy_id,
            )
        )
        if policy is None:
            policy = RetentionPolicy(
                organization_id=organization_id,
                policy_key=config.policy_id,
                raw_days=config.raw_days,
                quarantine_days=config.quarantine_days,
                export_days=config.export_days,
                audit_days=config.audit_days,
                active=True,
            )
            self.session.add(policy)
        else:
            policy.raw_days = config.raw_days
            policy.quarantine_days = config.quarantine_days
            policy.export_days = config.export_days
            policy.audit_days = config.audit_days
        self.session.commit()
        return policy

    def apply_export_retention(
        self,
        organization_id: uuid.UUID,
        policy: RetentionPolicy,
        dry_run: bool = True,
        as_of: datetime | None = None,
    ) -> RetentionOutcome:
        reference = as_of or datetime.now(UTC)
        cutoff = reference - timedelta(days=policy.export_days)
        snapshots = list(
            self.session.scalars(
                select(ExportSnapshot)
                .join(ExportDefinition)
                .where(
                    ExportDefinition.organization_id == organization_id,
                    ExportSnapshot.published_at < cutoff,
                )
            )
        )
        deleted: list[str] = []
        if not dry_run:
            root = self.export_root.resolve(strict=True)
            for snapshot in snapshots:
                parsed = urlparse(snapshot.storage_uri)
                if parsed.scheme != "file":
                    raise ConnectorError(
                        "retention_uri_unsupported", "Retention supports local file URIs only"
                    )
                path = Path(unquote(parsed.path)).resolve(strict=True)
                if not path.is_relative_to(root):
                    raise ConnectorError(
                        "retention_path_outside_root", "Retention path is outside export root"
                    )
                path.unlink()
                deleted.append(str(path))
                self.session.delete(snapshot)
            self.session.commit()
        return RetentionOutcome(
            candidate_ids=[snapshot.id for snapshot in snapshots],
            deleted_files=deleted,
            dry_run=dry_run,
        )
