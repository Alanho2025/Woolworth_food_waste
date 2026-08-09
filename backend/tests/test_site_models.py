from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models import (
    Organisation,
    Site,
    SiteLocation,
    navigation_location_statement,
)


def test_organisation_can_have_multiple_operational_sites(postgres_session: Session) -> None:
    organisation = Organisation(name="Woolworths")
    organisation.sites.extend(
        [
            Site(name="Auckland store", site_type="store"),
            Site(name="Auckland service site", site_type="service_site"),
        ]
    )

    postgres_session.add(organisation)
    postgres_session.commit()

    stored = postgres_session.get(Organisation, organisation.id)
    assert stored is not None
    assert {site.site_type for site in stored.sites} == {"store", "service_site"}


def test_site_keeps_public_and_operational_locations_separately(
    postgres_session: Session,
) -> None:
    confirmed_at = datetime(2026, 8, 9, 10, 0, tzinfo=UTC)
    site = Site(name="KiwiHarvest branch", site_type="branch")
    site.locations.extend(
        [
            SiteLocation(
                location_type="public_address",
                precision_level="address_level",
                verification_status="unverified",
                visibility="public",
                address_line1="100 Example Street",
                city="Auckland",
            ),
            SiteLocation(
                location_type="pickup_point",
                precision_level="exact",
                verification_status="operator_confirmed",
                visibility="operational",
                address_line1="100 Example Street, loading entrance",
                city="Auckland",
                latitude=Decimal("-36.848500"),
                longitude=Decimal("174.763300"),
                verified_at=confirmed_at,
            ),
        ]
    )
    organisation = Organisation(name="KiwiHarvest")
    organisation.sites.append(site)

    postgres_session.add(organisation)
    postgres_session.commit()

    stored = postgres_session.get(Site, site.id)
    assert stored is not None
    assert {location.location_type for location in stored.locations} == {
        "public_address",
        "pickup_point",
    }


def test_navigation_statement_is_fail_closed_for_unverified_public_and_protected_points(
    postgres_session: Session,
) -> None:
    as_of = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
    site = Site(name="Recipient site", site_type="service_site")
    site.locations.extend(
        [
            SiteLocation(
                location_type="pickup_point",
                precision_level="exact",
                verification_status="operator_confirmed",
                visibility="operational",
                latitude=Decimal("-36.848500"),
                longitude=Decimal("174.763300"),
                valid_from=as_of - timedelta(hours=1),
                verified_at=as_of - timedelta(hours=2),
            ),
            SiteLocation(
                location_type="receiving_point",
                precision_level="exact",
                verification_status="unverified",
                visibility="operational",
                latitude=Decimal("-36.849000"),
                longitude=Decimal("174.764000"),
                valid_from=as_of - timedelta(hours=1),
            ),
            SiteLocation(
                location_type="pickup_point",
                precision_level="exact",
                verification_status="operator_confirmed",
                visibility="public",
                latitude=Decimal("-36.850000"),
                longitude=Decimal("174.765000"),
                valid_from=as_of - timedelta(hours=1),
                verified_at=as_of - timedelta(hours=2),
            ),
            SiteLocation(
                location_type="receiving_point",
                precision_level="exact",
                verification_status="operator_confirmed",
                visibility="protected",
                latitude=Decimal("-36.851000"),
                longitude=Decimal("174.766000"),
                valid_from=as_of - timedelta(hours=1),
                verified_at=as_of - timedelta(hours=2),
            ),
            SiteLocation(
                location_type="pickup_point",
                precision_level="exact",
                verification_status="operator_confirmed",
                visibility="operational",
                latitude=Decimal("-36.852000"),
                longitude=Decimal("174.767000"),
                valid_from=as_of - timedelta(days=2),
                valid_until=as_of - timedelta(hours=1),
                verified_at=as_of - timedelta(days=2),
            ),
        ]
    )
    organisation = Organisation(name="Community recipient")
    organisation.sites.append(site)

    inactive_site = Site(
        name="Inactive recipient site",
        site_type="service_site",
        status="inactive",
    )
    inactive_site.locations.append(
        SiteLocation(
            location_type="receiving_point",
            precision_level="exact",
            verification_status="operator_confirmed",
            visibility="operational",
            latitude=Decimal("-36.853000"),
            longitude=Decimal("174.768000"),
            valid_from=as_of - timedelta(hours=1),
            verified_at=as_of - timedelta(hours=2),
        )
    )
    organisation.sites.append(inactive_site)
    postgres_session.add(organisation)
    postgres_session.commit()

    navigation_locations = postgres_session.scalars(
        navigation_location_statement(as_of=as_of)
    ).all()

    assert len(navigation_locations) == 1
    assert navigation_locations[0].visibility == "operational"
    assert navigation_locations[0].verification_status == "operator_confirmed"


def test_site_location_constraints_reject_invalid_values(postgres_session: Session) -> None:
    organisation = Organisation(name="Woolworths")
    site = Site(name="Auckland store", site_type="store")
    organisation.sites.append(site)
    postgres_session.add(organisation)
    postgres_session.flush()

    postgres_session.add(
        SiteLocation(
            site_id=site.id,
            location_type="pickup_point",
            precision_level="exact",
            verification_status="operator_confirmed",
            visibility="operational",
            latitude=Decimal("-91"),
            longitude=Decimal("174.763300"),
            verified_at=datetime(2026, 8, 9, tzinfo=UTC),
        )
    )
    with pytest.raises(IntegrityError):
        postgres_session.commit()

    postgres_session.rollback()
    postgres_session.add(
        SiteLocation(
            site_id=site.id,
            location_type="receiving_point",
            precision_level="exact",
            verification_status="operator_confirmed",
            visibility="operational",
            latitude=Decimal("-36.848500"),
            verified_at=datetime(2026, 8, 9, tzinfo=UTC),
        )
    )
    with pytest.raises(IntegrityError):
        postgres_session.commit()

    postgres_session.rollback()
    postgres_session.add(
        SiteLocation(
            site_id=site.id,
            location_type="receiving_point",
            precision_level="exact",
            verification_status="operator_confirmed",
            visibility="operational",
            latitude=Decimal("-36.848500"),
            longitude=Decimal("174.763300"),
        )
    )
    with pytest.raises(IntegrityError):
        postgres_session.commit()


def test_site_and_organisation_cannot_be_deleted_with_location_history(
    postgres_session: Session,
) -> None:
    organisation = Organisation(name="Community partner")
    site = Site(name="Recipient site", site_type="service_site")
    site.locations.append(
        SiteLocation(
            location_type="public_address",
            precision_level="address_level",
            verification_status="unverified",
            visibility="public",
            address_line1="100 Example Street",
        )
    )
    organisation.sites.append(site)
    postgres_session.add(organisation)
    postgres_session.commit()

    with pytest.raises(IntegrityError):
        postgres_session.execute(delete(Site).where(Site.id == site.id))
        postgres_session.commit()

    postgres_session.rollback()
    with pytest.raises(IntegrityError):
        postgres_session.execute(delete(Organisation).where(Organisation.id == organisation.id))
        postgres_session.commit()

    postgres_session.rollback()
    assert postgres_session.scalars(select(Site)).one().id == site.id
