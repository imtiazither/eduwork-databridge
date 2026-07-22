import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from eduwork_databridge.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_type: Mapped[str] = mapped_column(String(50), nullable=False, default="employer")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    parent_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class OrganizationUnit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organization_units"
    __table_args__ = (
        UniqueConstraint("organization_id", "external_key", name="uq_org_unit_external_key"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    parent_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organization_units.id"), nullable=True
    )
    external_key: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_type: Mapped[str] = mapped_column(String(50), nullable=False, default="department")
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)


class Person(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "persons"
    __table_args__ = (Index("ix_person_org_status", "organization_id", "status"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    given_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    family_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    preferred_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)


class ExternalIdentity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "external_identities"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "source_system_id",
            "identity_type",
            "identity_value_hash",
            name="uq_external_identity_scope",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("persons.id"), nullable=False, index=True
    )
    source_system_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("source_systems.id"), nullable=False, index=True
    )
    identity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    identity_value: Mapped[str] = mapped_column(String(512), nullable=False)
    identity_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trusted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class RoleAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "role_assignments"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("persons.id"), nullable=False, index=True
    )
    organization_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organization_units.id"), nullable=True
    )
    role_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)


class LearningProgram(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_programs"
    __table_args__ = (
        UniqueConstraint("organization_id", "external_key", name="uq_program_external_key"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    external_key: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    program_type: Mapped[str] = mapped_column(String(50), nullable=False, default="training")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")


class LearningOffering(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_offerings"
    __table_args__ = (
        UniqueConstraint("organization_id", "external_key", name="uq_offering_external_key"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    program_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("learning_programs.id"), nullable=True, index=True
    )
    external_key: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    offering_type: Mapped[str] = mapped_column(String(50), nullable=False, default="course")
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="planned")


class Participation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "participations"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "person_id",
            "offering_id",
            "source_record_key",
            name="uq_participation_source_record",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("persons.id"), nullable=False, index=True
    )
    offering_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("learning_offerings.id"), nullable=False, index=True
    )
    source_record_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="assigned")
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ExperienceEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "experience_events"
    __table_args__ = (
        UniqueConstraint("organization_id", "source_system_id", "event_key", name="uq_event_key"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    source_system_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("source_systems.id"), nullable=False, index=True
    )
    person_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("persons.id"), nullable=True, index=True
    )
    offering_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("learning_offerings.id"), nullable=True
    )
    event_key: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class AssessmentDefinition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_definitions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    external_key: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    maximum_score: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    passing_score: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)


class AssessmentAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_attempts"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("assessment_definitions.id"), nullable=False, index=True
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("persons.id"), nullable=False, index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AssessmentResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_results"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("assessment_attempts.id"), nullable=False, unique=True
    )
    raw_score: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    normalized_score: Mapped[float | None] = mapped_column(Numeric(8, 6), nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(50), nullable=True)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CompetencyDefinition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competency_definitions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    external_key: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    framework_uri: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    parent_competency_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        # Explicit name: the convention-derived one exceeds PostgreSQL's
        # 63-character identifier limit.
        ForeignKey(
            "competency_definitions.id", name="fk_competency_definitions_parent_competency_id"
        ),
        nullable=True,
    )


class CompetencyAlignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competency_alignments"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    competency_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("competency_definitions.id"), nullable=False, index=True
    )
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    alignment_type: Mapped[str] = mapped_column(String(50), nullable=False, default="teaches")


class CredentialDefinition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "credential_definitions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    external_key: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    credential_type: Mapped[str] = mapped_column(String(50), nullable=False, default="certificate")
    issuer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    public_uri: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    expires: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CredentialAward(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "credential_awards"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    credential_definition_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        # Explicit name: the convention-derived one exceeds PostgreSQL's
        # 63-character identifier limit.
        ForeignKey(
            "credential_definitions.id", name="fk_credential_awards_credential_definition_id"
        ),
        nullable=False,
        index=True,
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("persons.id"), nullable=False, index=True
    )
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    evidence_uri: Mapped[str | None] = mapped_column(String(1000), nullable=True)
