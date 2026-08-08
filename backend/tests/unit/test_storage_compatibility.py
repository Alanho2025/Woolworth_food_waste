"""Storage compatibility (foodflow_clean_code_spec.md 10.1, group 2).

STATUS: implemented and unit-tested, but NEVER EXERCISED BY THE DEMO. The
scripted scenario is entirely ambient, and B — the only chilled-only
organisation — is excluded on category before storage is ever the deciding
factor (docs/assumption_audit.md C-6). The README status table must say so.

That is precisely why the rule needs its own tests rather than incidental
coverage: nothing in the demo journey would notice if it were inverted.
"""

from __future__ import annotations

from backend.app.contracts.core import StorageType
from backend.app.domain.clock import PinnedClock
from backend.app.domain.errors import ErrorCode
from backend.tests.support import domain_api, world


def test_a_chilled_only_organisation_does_not_support_ambient_storage() -> None:
    """SEEDED WORLD -> read Community B's supported storage -> ambient absent."""
    assert StorageType.AMBIENT not in world.community_b().supported_storage


def test_ambient_donation_to_a_chilled_only_organisation_is_storage_incompatible(
    demo_clock: PinnedClock,
) -> None:
    """AMBIENT DONATION + CHILLED-ONLY ORG -> assess -> storage_compatible is False."""
    assessment = domain_api.assess_one(
        donation=world.donation(), community=world.community_b(), clock=demo_clock
    )
    assert assessment.storage_compatible is False


def test_ambient_donation_to_an_ambient_capable_organisation_is_storage_compatible(
    demo_clock: PinnedClock,
) -> None:
    """AMBIENT DONATION + AMBIENT-CAPABLE ORG -> assess -> storage_compatible is True."""
    assessment = domain_api.assess_one(
        donation=world.donation(), community=world.community_d(), clock=demo_clock
    )
    assert assessment.storage_compatible is True


def test_storage_incompatibility_is_reported_under_its_own_error_code(
    demo_clock: PinnedClock,
) -> None:
    """CATEGORY-OK BUT STORAGE-WRONG ORG -> assess -> STORAGE_INCOMPATIBLE.

    Built by taking Community D — which accepts vegetables — and removing
    ambient from its storage. Without this construction the demo world can never
    distinguish a storage failure from a category failure, because B fails both
    and the category check reports first.
    """
    frozen_only_d = world.community_d().model_copy(
        update={"supported_storage": [StorageType.FROZEN]}
    )
    assessment = domain_api.assess_one(
        donation=world.donation(), community=frozen_only_d, clock=demo_clock
    )
    assert assessment.category_compatible is True, "isolate storage from category"
    assert assessment.storage_compatible is False
    codes = [exclusion.code for exclusion in assessment.exclusions]
    assert ErrorCode.STORAGE_INCOMPATIBLE in codes, codes
