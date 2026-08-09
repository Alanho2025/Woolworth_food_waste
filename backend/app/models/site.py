"""Operational sites, typed locations, and the safe navigation selector."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
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


class Site(Base):
    """An operational site belonging to one organisation."""

    __tablename__ = "sites"
    __table_args__ = (
        CheckConstraint(
            "site_type IN ('store', 'branch', 'warehouse', 'service_site')",
            name="ck_sites_site_type",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_sites_status",
        ),
        UniqueConstraint(
            "id",
            "organisation_id",
            name="uq_sites_id_organisation",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal stable identifier for this operational site.",
    )
    organisation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Organisation that owns or operates this site.",
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Current site display name; not used as the internal identity.",
    )
    site_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Controlled site kind: store, branch, warehouse, or service_site.",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="active",
        server_default="active",
        comment="Lifecycle state; inactive sites remain available to history.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When this site identity was created.",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When the site identity fields were last changed.",
    )

    organisation: Mapped[Organisation] = relationship(back_populates="sites")
    locations: Mapped[list["SiteLocation"]] = relationship(
        back_populates="site",
        passive_deletes=True,
    )


class SiteLocation(Base):
    """A typed, time-bounded location record for a site."""

    __tablename__ = "site_locations"
    __table_args__ = (
        CheckConstraint(
            "location_type IN ('public_address', 'map_point', 'pickup_point', 'receiving_point')",
            name="ck_site_locations_location_type",
        ),
        CheckConstraint(
            "precision_level IN ('exact', 'address_level', 'site_centroid', 'approximate')",
            name="ck_site_locations_precision_level",
        ),
        CheckConstraint(
            "verification_status IN ('unverified', 'operator_confirmed')",
            name="ck_site_locations_verification_status",
        ),
        CheckConstraint(
            "visibility IN ('public', 'operational', 'protected')",
            name="ck_site_locations_visibility",
        ),
        CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL) "
            "OR (latitude IS NOT NULL AND longitude IS NOT NULL)",
            name="ck_site_locations_coordinate_pair",
        ),
        CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name="ck_site_locations_latitude_range",
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="ck_site_locations_longitude_range",
        ),
        CheckConstraint(
            "address_line1 IS NOT NULL OR (latitude IS NOT NULL AND longitude IS NOT NULL)",
            name="ck_site_locations_has_address_or_point",
        ),
        CheckConstraint(
            "(verification_status = 'unverified' AND verified_at IS NULL) "
            "OR (verification_status = 'operator_confirmed' AND verified_at IS NOT NULL)",
            name="ck_site_locations_verification_time",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="ck_site_locations_valid_period",
        ),
        UniqueConstraint(
            "id",
            "site_id",
            name="uq_site_locations_id_site",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal identifier for this location record and its validity period.",
    )
    site_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sites.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Site to which this location record belongs.",
    )
    location_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Address, research map point, pickup point, or receiving point.",
    )
    precision_level: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        comment="Coordinate / address precision used to judge navigation safety.",
    )
    verification_status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="unverified",
        server_default="unverified",
        comment="Whether an operator has confirmed this location for operations.",
    )
    visibility: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="public",
        server_default="public",
        comment="Public, operational-only, or protected visibility boundary.",
    )
    address_line1: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Street address when available; may be absent for a point-only candidate.",
    )
    suburb: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Suburb or locality from the source location.",
    )
    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="City or district from the source location.",
    )
    region: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Region from the source location.",
    )
    postal_code: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="Postal code when available; stored as text to preserve formatting.",
    )
    country_code: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        default="NZ",
        server_default="NZ",
        comment="ISO-like country code for the location; first slice is NZ-only.",
    )
    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(9, 6),
        nullable=True,
        comment="Latitude in decimal degrees; must be paired with longitude.",
    )
    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(9, 6),
        nullable=True,
        comment="Longitude in decimal degrees; must be paired with latitude.",
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="Inclusive start of this location record's validity.",
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Exclusive end; a correction creates a new record instead of overwriting history.",
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the operator confirmation was recorded; required for confirmed points.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When this location record was stored.",
    )

    site: Mapped[Site] = relationship(back_populates="locations")


def navigation_location_statement(*, as_of: datetime) -> Select[tuple[SiteLocation]]:
    """Return only current, operator-confirmed operational points for navigation."""

    return (
        select(SiteLocation)
        .join(SiteLocation.site)
        .where(
            Site.status == "active",
            SiteLocation.location_type.in_(("pickup_point", "receiving_point")),
            SiteLocation.precision_level == "exact",
            SiteLocation.verification_status == "operator_confirmed",
            SiteLocation.visibility == "operational",
            SiteLocation.valid_from <= as_of,
            or_(SiteLocation.valid_until.is_(None), SiteLocation.valid_until > as_of),
        )
    )
