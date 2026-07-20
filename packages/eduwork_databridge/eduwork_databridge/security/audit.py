import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from eduwork_databridge.db.models.control import AuditEvent
from eduwork_databridge.observability import sanitize_attributes
from eduwork_databridge.security.identity import Actor


class AuditService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        actor: Actor,
        action: str,
        resource_type: str,
        resource_id: str,
        organization_id: uuid.UUID | None,
        correlation_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            occurred_at=datetime.now(UTC),
            organization_id=organization_id,
            actor_id=actor.actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            correlation_id=correlation_id,
            details_json=sanitize_attributes(details or {}),
        )
        self.session.add(event)
        self.session.commit()
        return event

    def list_for_organization(
        self,
        organization_id: uuid.UUID,
        limit: int = 100,
    ) -> list[AuditEvent]:
        return list(
            self.session.scalars(
                select(AuditEvent)
                .where(AuditEvent.organization_id == organization_id)
                .order_by(AuditEvent.occurred_at.desc())
                .limit(min(max(limit, 1), 1000))
            )
        )
