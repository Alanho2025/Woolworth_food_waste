from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models import Base, Organisation, OrganisationRole


def test_phase_one_registers_identity_tables() -> None:
    tables = set(Base.metadata.tables)

    assert {"organisations", "organisation_roles"} <= tables


def test_organisation_can_hold_multiple_time_bounded_roles(postgres_session: Session) -> None:
    role_start = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
    organisation = Organisation(name="KiwiHarvest")
    organisation.roles.extend(
        [
            OrganisationRole(role_type="food_rescue_operator", valid_from=role_start),
            OrganisationRole(
                role_type="recipient",
                valid_from=role_start,
                valid_until=role_start + timedelta(days=365),
            ),
        ]
    )

    postgres_session.add(organisation)
    postgres_session.commit()

    stored = postgres_session.get(Organisation, organisation.id)
    assert stored is not None
    assert {role.role_type for role in stored.roles} == {
        "food_rescue_operator",
        "recipient",
    }


def test_role_constraints_reject_unknown_role_and_invalid_period(
    postgres_session: Session,
) -> None:
    organisation = Organisation(name="Woolworths")
    postgres_session.add(organisation)
    postgres_session.flush()

    postgres_session.add(
        OrganisationRole(
            organisation_id=organisation.id,
            role_type="warehouse",
        )
    )
    with pytest.raises(IntegrityError):
        postgres_session.commit()

    postgres_session.rollback()
    postgres_session.add(
        OrganisationRole(
            organisation_id=organisation.id,
            role_type="donor",
            valid_from=datetime(2026, 8, 10, tzinfo=UTC),
            valid_until=datetime(2026, 8, 9, tzinfo=UTC),
        )
    )
    with pytest.raises(IntegrityError):
        postgres_session.commit()


def test_parent_identity_cannot_be_deleted_while_role_history_exists(
    postgres_session: Session,
) -> None:
    organisation = Organisation(name="Community Food Partner")
    organisation.roles.append(OrganisationRole(role_type="recipient"))
    postgres_session.add(organisation)
    postgres_session.commit()

    with pytest.raises(IntegrityError):
        postgres_session.execute(delete(Organisation).where(Organisation.id == organisation.id))
        postgres_session.commit()

    postgres_session.rollback()
    assert postgres_session.is_active
