"""Business actors and time-bounded organisation/site memberships."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    func,
    or_,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import Select
from sqlalchemy.types import Uuid

from backend.app.models.base import Base
from backend.app.models.organisation import Organisation
from backend.app.models.site import Site


class User(Base):
    """A business actor identity with deferred authentication credentials."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_users_status",
        ),
        CheckConstraint(
            "(oauth_provider IS NULL) = (oauth_subject IS NULL)",
            name="ck_users_oauth_identity_pair",
        ),
        CheckConstraint(
            "password_hash IS NULL OR email IS NOT NULL",
            name="ck_users_password_requires_email",
        ),
        UniqueConstraint(
            "oauth_provider",
            "oauth_subject",
            name="uq_users_oauth_identity",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal actor identity; not an authentication provider subject.",
    )
    display_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Operational display name used by authorised workflow actors.",
    )
    email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
        comment=(
            "Optional login/contact identity; normalise before writing and "
            "protect from general API reads."
        ),
    )
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Argon2id/bcrypt-style encoded hash only; never store a plaintext password.",
    )
    oauth_provider: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="OAuth/OIDC provider namespace, stored with oauth_subject.",
    )
    oauth_subject: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Opaque provider subject; not a display name or internal actor ID.",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="active",
        server_default="active",
        comment="Actor lifecycle; inactive users remain available to history.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When this business actor identity was created.",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When this business actor identity was last changed.",
    )

    memberships: Mapped[list["OrganisationMembership"]] = relationship(
        back_populates="user",
        passive_deletes=True,
    )


class OrganisationMembership(Base):
    """A role and scope held by one user for a bounded period."""

    __tablename__ = "organisation_memberships"
    __table_args__ = (
        CheckConstraint(
            "membership_role IN ('driver', 'coordinator', 'recipient_responder')",
            name="ck_organisation_memberships_role",
        ),
        CheckConstraint(
            "scope_type IN ('organisation', 'site')",
            name="ck_organisation_memberships_scope_type",
        ),
        CheckConstraint(
            "(scope_type = 'organisation' AND site_id IS NULL) "
            "OR (scope_type = 'site' AND site_id IS NOT NULL)",
            name="ck_organisation_memberships_scope_target",
        ),
        CheckConstraint(
            "membership_role <> 'recipient_responder' OR scope_type = 'site'",
            name="ck_organisation_memberships_recipient_site_scope",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="ck_organisation_memberships_valid_period",
        ),
        ForeignKeyConstraint(
            ["site_id", "organisation_id"],
            ["sites.id", "sites.organisation_id"],
            ondelete="RESTRICT",
            name="fk_organisation_memberships_site_organisation",
        ),
        UniqueConstraint(
            "user_id",
            "organisation_id",
            "site_id",
            "membership_role",
            "valid_from",
            name="uq_organisation_memberships_identity_period",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal identifier for this membership period.",
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Business actor holding this membership.",
    )
    organisation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Organisation in which the role is valid.",
    )
    site_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        comment="Target site when scope_type is site; NULL means organisation scope.",
    )
    scope_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="organisation",
        server_default="organisation",
        comment="Explicit authority scope: organisation or site.",
    )
    membership_role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Controlled role: driver, coordinator, or recipient_responder.",
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="Inclusive start of the membership validity period.",
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Exclusive end; a new membership period preserves history.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When this membership period was recorded.",
    )

    user: Mapped[User] = relationship(back_populates="memberships")
    organisation: Mapped[Organisation] = relationship(back_populates="memberships")
    site: Mapped[Site | None] = relationship(viewonly=True)


Index(
    "uq_users_email_ci",
    func.lower(User.email),
    unique=True,
)


def active_membership_statement(*, as_of: datetime) -> Select[tuple[OrganisationMembership]]:
    """Return memberships held by active users at a specific time."""

    return (
        select(OrganisationMembership)
        .join(OrganisationMembership.user)
        .where(
            User.status == "active",
            OrganisationMembership.valid_from <= as_of,
            or_(
                OrganisationMembership.valid_until.is_(None),
                OrganisationMembership.valid_until > as_of,
            ),
        )
    )
