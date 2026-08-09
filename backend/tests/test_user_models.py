from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models import (
    Organisation,
    OrganisationMembership,
    Site,
    User,
    active_membership_statement,
)


def test_user_can_hold_multiple_organisation_and_site_memberships(
    postgres_session: Session,
) -> None:
    organisation = Organisation(name="KiwiHarvest")
    site = Site(name="Auckland branch", site_type="branch")
    organisation.sites.append(site)
    user = User(display_name="Driver One")
    postgres_session.add_all([organisation, user])
    postgres_session.flush()

    user.memberships.extend(
        [
            OrganisationMembership(
                organisation_id=organisation.id,
                membership_role="driver",
            ),
            OrganisationMembership(
                organisation_id=organisation.id,
                site_id=site.id,
                scope_type="site",
                membership_role="recipient_responder",
            ),
        ]
    )
    postgres_session.commit()

    stored = postgres_session.get(User, user.id)
    assert stored is not None
    assert {membership.membership_role for membership in stored.memberships} == {
        "driver",
        "recipient_responder",
    }


def test_recipient_responder_requires_site_scope(postgres_session: Session) -> None:
    organisation = Organisation(name="Community recipient")
    user = User(display_name="Recipient staff")
    postgres_session.add_all([organisation, user])
    postgres_session.flush()

    postgres_session.add(
        OrganisationMembership(
            user_id=user.id,
            organisation_id=organisation.id,
            membership_role="recipient_responder",
        )
    )
    with pytest.raises(IntegrityError):
        postgres_session.commit()


def test_site_scoped_membership_cannot_cross_organisation(
    postgres_session: Session,
) -> None:
    first_organisation = Organisation(name="KiwiHarvest")
    first_site = Site(name="KiwiHarvest branch", site_type="branch")
    first_organisation.sites.append(first_site)
    second_organisation = Organisation(name="Community recipient")
    user = User(display_name="Recipient staff")
    postgres_session.add_all([first_organisation, second_organisation, user])
    postgres_session.flush()

    postgres_session.add(
        OrganisationMembership(
            user_id=user.id,
            organisation_id=second_organisation.id,
            site_id=first_site.id,
            scope_type="site",
            membership_role="recipient_responder",
        )
    )
    with pytest.raises(IntegrityError):
        postgres_session.commit()


def test_active_membership_excludes_expired_memberships_and_inactive_users(
    postgres_session: Session,
) -> None:
    as_of = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
    organisation = Organisation(name="KiwiHarvest")
    active_user = User(display_name="Active driver")
    inactive_user = User(display_name="Former driver", status="inactive")
    postgres_session.add_all([organisation, active_user, inactive_user])
    postgres_session.flush()

    active_user.memberships.append(
        OrganisationMembership(
            organisation_id=organisation.id,
            membership_role="driver",
            valid_from=as_of - timedelta(hours=1),
        )
    )
    active_user.memberships.append(
        OrganisationMembership(
            organisation_id=organisation.id,
            membership_role="coordinator",
            valid_from=as_of - timedelta(days=2),
            valid_until=as_of - timedelta(hours=1),
        )
    )
    inactive_user.memberships.append(
        OrganisationMembership(
            organisation_id=organisation.id,
            membership_role="driver",
            valid_from=as_of - timedelta(hours=1),
        )
    )
    postgres_session.commit()

    active_memberships = postgres_session.scalars(active_membership_statement(as_of=as_of)).all()

    assert len(active_memberships) == 1
    assert active_memberships[0].user_id == active_user.id
    assert active_memberships[0].membership_role == "driver"
    assert postgres_session.get(User, inactive_user.id) is not None


def test_user_and_organisation_cannot_be_deleted_with_membership_history(
    postgres_session: Session,
) -> None:
    organisation = Organisation(name="KiwiHarvest")
    user = User(display_name="Driver")
    postgres_session.add_all([organisation, user])
    postgres_session.flush()
    membership = OrganisationMembership(
        user_id=user.id,
        organisation_id=organisation.id,
        membership_role="driver",
    )
    postgres_session.add(membership)
    postgres_session.commit()

    with pytest.raises(IntegrityError):
        postgres_session.execute(delete(User).where(User.id == user.id))
        postgres_session.commit()

    postgres_session.rollback()
    with pytest.raises(IntegrityError):
        postgres_session.execute(delete(Organisation).where(Organisation.id == organisation.id))
        postgres_session.commit()

    postgres_session.rollback()
    assert postgres_session.get(OrganisationMembership, membership.id) is not None


def test_user_identity_fields_support_deferred_local_and_oauth_auth(
    postgres_session: Session,
) -> None:
    local_user = User(
        display_name="Local actor",
        email="Driver@Example.nz",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$encoded-placeholder",
    )
    oauth_user = User(
        display_name="OAuth actor",
        oauth_provider="example_oidc",
        oauth_subject="provider-subject-123",
    )
    postgres_session.add_all([local_user, oauth_user])
    postgres_session.commit()

    assert local_user.id is not None
    assert oauth_user.id is not None
    stored_local_user = postgres_session.get(User, local_user.id)
    assert stored_local_user is not None
    assert stored_local_user.email == "Driver@Example.nz"


def test_oauth_provider_and_subject_must_be_supplied_together(
    postgres_session: Session,
) -> None:
    postgres_session.add(User(display_name="Incomplete OAuth actor", oauth_subject="subject-only"))

    with pytest.raises(IntegrityError):
        postgres_session.commit()


def test_oauth_identity_is_unique_within_provider(postgres_session: Session) -> None:
    postgres_session.add_all(
        [
            User(
                display_name="First OAuth actor",
                oauth_provider="example_oidc",
                oauth_subject="same-subject",
            ),
            User(
                display_name="Second OAuth actor",
                oauth_provider="example_oidc",
                oauth_subject="same-subject",
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        postgres_session.commit()


def test_password_hash_requires_email(postgres_session: Session) -> None:
    postgres_session.add(
        User(
            display_name="Incomplete local actor",
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$encoded-placeholder",
        )
    )

    with pytest.raises(IntegrityError):
        postgres_session.commit()


def test_email_is_case_insensitively_unique(postgres_session: Session) -> None:
    postgres_session.add_all(
        [
            User(display_name="First actor", email="person@example.nz"),
            User(display_name="Second actor", email="PERSON@example.nz"),
        ]
    )

    with pytest.raises(IntegrityError):
        postgres_session.commit()


def test_scope_type_must_match_site_target(postgres_session: Session) -> None:
    organisation = Organisation(name="KiwiHarvest")
    site = Site(name="Auckland branch", site_type="branch")
    organisation.sites.append(site)
    user = User(display_name="Scoped driver")
    postgres_session.add_all([organisation, user])
    postgres_session.flush()
    postgres_session.add(
        OrganisationMembership(
            user_id=user.id,
            organisation_id=organisation.id,
            site_id=site.id,
            scope_type="organisation",
            membership_role="driver",
        )
    )

    with pytest.raises(IntegrityError):
        postgres_session.commit()
