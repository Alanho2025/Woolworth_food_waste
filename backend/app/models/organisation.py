"""Organisation identity and time-bounded organisation roles."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.site import Site
    from backend.app.models.user import OrganisationMembership


class Organisation(Base):
    """A stable identity for a donor, recipient, hub, or food-rescue organisation."""

    __tablename__ = "organisations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_organisations_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal stable identifier; not a display name or external source identifier.",
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Current display name; renames must not change the internal identity.",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="active",
        server_default="active",
        comment="Lifecycle state; inactive organisations remain available to history.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When this canonical identity was created.",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When the canonical identity fields were last changed.",
    )

    roles: Mapped[list["OrganisationRole"]] = relationship(
        back_populates="organisation",
        passive_deletes=True,
    )
    sites: Mapped[list["Site"]] = relationship(
        back_populates="organisation",
        passive_deletes=True,
    )
    memberships: Mapped[list["OrganisationMembership"]] = relationship(
        back_populates="organisation",
        passive_deletes=True,
    )


class OrganisationRole(Base):
    """A time-bounded role held by an organisation."""

    __tablename__ = "organisation_roles"
    __table_args__ = (
        CheckConstraint(
            "role_type IN ('donor', 'recipient', 'hub', 'food_rescue_operator')",
            name="ck_organisation_roles_role_type",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="ck_organisation_roles_valid_period",
        ),
        UniqueConstraint(
            "organisation_id",
            "role_type",
            "valid_from",
            name="uq_organisation_roles_identity_period",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal identifier for this role period.",
    )
    organisation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Organisation whose role is represented.",
    )
    role_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Controlled role: donor, recipient, hub, or food_rescue_operator.",
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="Inclusive start of the role's validity period.",
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Exclusive end of the role's validity period; NULL means no recorded end.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When this role period was recorded.",
    )

    organisation: Mapped[Organisation] = relationship(back_populates="roles")
