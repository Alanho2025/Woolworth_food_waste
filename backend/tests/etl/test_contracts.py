import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from backend.app.etl.contracts import (
    BundleEnvelope,
    CanonicalBundleContent,
    CanonicalEntityRef,
    CanonicalRecord,
    DataOrigin,
    DerivedMetadata,
    ETLMetadata,
    EvidenceRegister,
    FieldProvenance,
    ObservedMetadata,
    RawPayloadEnvelope,
    SimulationMetadata,
    UnknownMetadata,
    bundle_content_checksum,
    deterministic_bundle_id,
    validate_raw_payload,
    validate_simulation_coverage,
)
from backend.app.models import Base

ROOT = Path(__file__).parents[3]
RULES_PATH = ROOT / "data/etl/rules/simulation-rules.v1.json"
EVIDENCE_PATH = ROOT / "data/etl/evidence/evidence-register.v1.json"


def valid_origin_variants() -> list[object]:
    return [
        ObservedMetadata(
            data_origin=DataOrigin.OBSERVED,
            source_id="source",
            snapshot_id="snapshot",
            retrieved_at=datetime(2026, 8, 9, tzinfo=UTC),
            observed_at=datetime(2026, 8, 8, tzinfo=UTC),
            raw_reference="snapshot.json#/records/1",
            source_checksum="a" * 64,
        ),
        DerivedMetadata(
            data_origin=DataOrigin.DERIVED,
            source_record_ids=["record-1"],
            transform_version="v1",
            function_name="normalize_record",
            input_checksum="b" * 64,
        ),
        SimulationMetadata(
            data_origin=DataOrigin.EVIDENCE_BACKED_SIMULATION,
            rule_ids=["rule-1"],
            evidence_ids=["evidence-1"],
            calibration_method="bounded_demo_value",
            allowed_values_or_range={"min": 1, "max": 5},
            unit="count",
            seed="demo-seed",
            confidence="medium",
            limitations=["not operational evidence"],
            generated_values={"value": 3},
        ),
        UnknownMetadata(
            data_origin=DataOrigin.UNKNOWN,
            reason="not published",
            missing_evidence=["current capacity"],
            promotion_gate="operator confirmation",
        ),
    ]


@pytest.mark.parametrize("origin", valid_origin_variants())
def test_origin_variants_accept_valid_metadata(origin: object) -> None:
    assert origin.data_origin in DataOrigin


@pytest.mark.parametrize(
    ("origin", "extra"),
    [
        (valid_origin_variants()[0], {"reason": "wrong variant"}),
        (valid_origin_variants()[1], {"source_id": "wrong variant"}),
        (valid_origin_variants()[2], {"promotion_gate": "wrong variant"}),
        (valid_origin_variants()[3], {"seed": "wrong variant"}),
    ],
)
def test_origin_variants_reject_extra_or_mismatched_fields(
    origin: object, extra: dict[str, str]
) -> None:
    payload = origin.model_dump(mode="python")  # type: ignore[union-attr]
    payload.update(extra)
    with pytest.raises(ValidationError):
        ETLMetadata(
            profile="realistic_demo",
            bundle_id="bundle",
            origin_metadata=payload,
            canonical_entity_refs=[],
        )


def test_raw_payload_rejects_nested_secret_and_oversize_without_truncating() -> None:
    metadata = ETLMetadata(
        profile="realistic_demo",
        bundle_id="bundle",
        origin_metadata=valid_origin_variants()[0],
        canonical_entity_refs=[
            CanonicalEntityRef(
                entity_type="source_record",
                entity_id="record-1",
                data_origin=DataOrigin.OBSERVED,
                source_refs=["source"],
                rule_refs=[],
            )
        ],
    )
    valid_envelope = RawPayloadEnvelope(source_payload={"safe": True}, etl_metadata=metadata)
    assert validate_raw_payload(valid_envelope)
    with pytest.raises(ValueError, match="secret-like"):
        RawPayloadEnvelope(
            source_payload={"nested": [{"Authorization": "do-not-store"}]},
            etl_metadata=metadata,
        )

    with pytest.raises(ValueError, match="65,536"):
        RawPayloadEnvelope(
            source_payload={"value": "x" * 70_000},
            etl_metadata=metadata,
        )


def test_raw_payload_rejects_secret_in_metadata_during_construction() -> None:
    simulation_metadata = SimulationMetadata(
        data_origin=DataOrigin.EVIDENCE_BACKED_SIMULATION,
        rule_ids=["rule-1"],
        evidence_ids=["evidence-1"],
        calibration_method="bounded_demo_value",
        allowed_values_or_range={"min": 1, "max": 5},
        unit="count",
        seed="demo-seed",
        confidence="medium",
        limitations=["not operational evidence"],
        generated_values={"nested": [{"PASSWORD_HASH": "do-not-store"}]},
    )
    with pytest.raises(ValueError, match="secret-like"):
        RawPayloadEnvelope(
            source_payload={"safe": True},
            etl_metadata=ETLMetadata(
                profile="realistic_demo",
                bundle_id="bundle",
                origin_metadata=simulation_metadata,
                canonical_entity_refs=[],
            ),
        )


def test_canonical_entity_ref_origin_semantics_are_fail_closed() -> None:
    with pytest.raises(ValidationError, match="observed and derived"):
        CanonicalEntityRef(
            entity_type="user",
            entity_id="user-1",
            data_origin=DataOrigin.OBSERVED,
            source_refs=[],
            rule_refs=["sim-users-v1"],
        )

    simulated = CanonicalEntityRef(
        entity_type="user",
        entity_id="user-1",
        data_origin=DataOrigin.EVIDENCE_BACKED_SIMULATION,
        source_refs=["calibration-source"],
        rule_refs=["sim-users-v1", "sim-memberships-v1"],
    )
    assert simulated.rule_refs == ["sim-users-v1", "sim-memberships-v1"]

    with pytest.raises(ValidationError, match="unknown entity"):
        CanonicalEntityRef(
            entity_type="user",
            entity_id="user-1",
            data_origin=DataOrigin.UNKNOWN,
            source_refs=["source"],
            rule_refs=[],
        )


def test_etl_metadata_rejects_duplicate_entity_refs_after_uuid_normalisation() -> None:
    first = CanonicalEntityRef(
        entity_type="user",
        entity_id=UUID("00000000-0000-0000-0000-000000000003"),
        data_origin=DataOrigin.OBSERVED,
        source_refs=["source"],
        rule_refs=[],
    )
    duplicate = first.model_copy(update={"entity_id": str(first.entity_id)})
    with pytest.raises(ValidationError, match="duplicate canonical entity reference"):
        ETLMetadata(
            profile="realistic_demo",
            bundle_id="bundle",
            origin_metadata=valid_origin_variants()[0],
            canonical_entity_refs=[first, duplicate],
        )


def test_bundle_checksum_and_id_are_stable_and_non_circular() -> None:
    first = CanonicalBundleContent(
        bundle_version="v1",
        profile="realistic_demo",
        as_of=date(2026, 8, 9),
        timezone="Pacific/Auckland",
        seed="demo-seed",
        expected_schema_revision="0cfadf2acb52",
        source_checksums={"b": "2", "a": "1"},
        records=[
            CanonicalRecord(
                entity_type="z",
                entity_id=UUID("00000000-0000-0000-0000-000000000002"),
                attributes={
                    "when": datetime(2026, 8, 9, tzinfo=UTC),
                    "n": Decimal("1.20"),
                },
                data_origin=DataOrigin.DERIVED,
                source_refs=["record-1"],
                rule_refs=[],
                field_provenance={
                    "entity_id": derived_field_provenance(),
                    "when": derived_field_provenance(),
                    "n": derived_field_provenance(),
                },
            ),
            CanonicalRecord(
                entity_type="a",
                entity_id="a-1",
                attributes={"value": 1},
                data_origin=DataOrigin.OBSERVED,
                source_refs=["a"],
                rule_refs=[],
                field_provenance={
                    "entity_id": observed_field_provenance("a"),
                    "value": observed_field_provenance("a"),
                },
            ),
        ],
    )
    second = first.model_copy(
        update={
            "source_checksums": {"a": "1", "b": "2"},
            "records": list(reversed(first.records)),
        }
    )
    first_checksum = bundle_content_checksum(first)
    assert first_checksum == bundle_content_checksum(second)
    assert deterministic_bundle_id(first) == deterministic_bundle_id(second)
    envelope = BundleEnvelope(
        bundle_id=deterministic_bundle_id(first), content=first, content_checksum=first_checksum
    )
    assert envelope.content_checksum == first_checksum
    assert "content_checksum" not in json.dumps(first.model_dump(mode="python"), default=str)

    changed = first.model_copy(update={"seed": "different-seed"})
    assert bundle_content_checksum(changed) != first_checksum


def test_bundle_rejects_duplicate_entity_key_after_uuid_normalisation() -> None:
    first = CanonicalRecord(
        entity_type="thing",
        entity_id=UUID("00000000-0000-0000-0000-000000000001"),
        attributes={},
        data_origin=DataOrigin.OBSERVED,
        source_refs=["source"],
        rule_refs=[],
        field_provenance={"entity_id": observed_field_provenance()},
    )
    duplicate = first.model_copy(update={"entity_id": str(first.entity_id)})
    with pytest.raises(ValidationError, match="duplicate canonical entity key"):
        CanonicalBundleContent(
            bundle_version="v1",
            profile="realistic_demo",
            as_of=date(2026, 8, 9),
            timezone="Pacific/Auckland",
            seed="seed",
            expected_schema_revision="revision",
            source_checksums={},
            records=[first, duplicate],
        )


def observed_field_provenance(source_id: str = "source") -> FieldProvenance:
    return FieldProvenance(
        data_origin=DataOrigin.OBSERVED,
        origin_metadata=ObservedMetadata(
            data_origin=DataOrigin.OBSERVED,
            source_id=source_id,
            snapshot_id="snapshot",
            retrieved_at=datetime(2026, 8, 9, tzinfo=UTC),
            raw_reference="snapshot.json#/records/1",
            source_checksum="a" * 64,
        ),
        source_refs=[source_id],
        rule_refs=[],
    )


def derived_field_provenance() -> FieldProvenance:
    return FieldProvenance(
        data_origin=DataOrigin.DERIVED,
        origin_metadata=DerivedMetadata(
            data_origin=DataOrigin.DERIVED,
            source_record_ids=["record-1"],
            transform_version="v1",
            function_name="normalize_record",
            input_checksum="b" * 64,
        ),
        source_refs=["record-1"],
        rule_refs=[],
    )


def mixed_record_payload() -> dict[str, object]:
    record = CanonicalRecord(
        entity_type="site_location",
        entity_id="site-location-1",
        attributes={"latitude": Decimal("-36.9000"), "verification_status": "operator_confirmed"},
        data_origin=DataOrigin.OBSERVED,
        source_refs=["source"],
        rule_refs=[],
        field_provenance={
            "entity_id": observed_field_provenance(),
            "latitude": observed_field_provenance(),
            "verification_status": FieldProvenance(
                data_origin=DataOrigin.EVIDENCE_BACKED_SIMULATION,
                origin_metadata=SimulationMetadata(
                    data_origin=DataOrigin.EVIDENCE_BACKED_SIMULATION,
                    rule_ids=["location-rule"],
                    evidence_ids=["location-evidence"],
                    calibration_method="scenario-only assertion",
                    allowed_values_or_range=["operator_confirmed"],
                    unit="status",
                    seed="demo-seed",
                    confidence="low",
                    limitations=["not real operator evidence"],
                    generated_values="operator_confirmed",
                ),
                source_refs=[],
                rule_refs=["location-rule"],
            ),
        },
    )
    return record.model_dump(mode="python")


def test_mixed_origin_record_requires_exact_field_provenance() -> None:
    record = CanonicalRecord.model_validate(mixed_record_payload())
    assert record.field_provenance["latitude"].data_origin == DataOrigin.OBSERVED
    assert (
        record.field_provenance["verification_status"].data_origin
        == DataOrigin.EVIDENCE_BACKED_SIMULATION
    )


def test_simulated_generated_value_must_match_actual_field() -> None:
    payload = mixed_record_payload()
    payload["attributes"]["verification_status"] = 999
    with pytest.raises(ValidationError, match="generated value"):
        CanonicalRecord.model_validate(payload)


def unknown_field_provenance() -> FieldProvenance:
    return FieldProvenance(
        data_origin=DataOrigin.UNKNOWN,
        origin_metadata=UnknownMetadata(
            data_origin=DataOrigin.UNKNOWN,
            reason="not published",
            missing_evidence=["current capacity"],
            promotion_gate="operator confirmation",
        ),
        source_refs=[],
        rule_refs=[],
    )


@pytest.mark.parametrize("unknown_value", [None, "unknown"])
def test_unknown_field_accepts_only_supported_sentinel_values(unknown_value: object) -> None:
    record = CanonicalRecord(
        entity_type="recipient_availability_snapshot",
        entity_id="availability-1",
        attributes={"available_quantity": unknown_value},
        data_origin=DataOrigin.OBSERVED,
        source_refs=["source"],
        rule_refs=[],
        field_provenance={
            "entity_id": observed_field_provenance(),
            "available_quantity": unknown_field_provenance(),
        },
    )
    assert record.attributes["available_quantity"] == unknown_value

    invalid = record.model_dump(mode="python")
    invalid["attributes"]["available_quantity"] = 123
    with pytest.raises(ValidationError, match="unknown field has concrete value"):
        CanonicalRecord.model_validate(invalid)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload["field_provenance"].pop("latitude"),
        lambda payload: payload["field_provenance"].update(
            {"extra": observed_field_provenance().model_dump(mode="python")}
        ),
        lambda payload: payload["field_provenance"]["verification_status"].update(
            {"data_origin": DataOrigin.OBSERVED}
        ),
        lambda payload: payload["field_provenance"]["verification_status"].update(
            {"rule_refs": []}
        ),
        lambda payload: payload["field_provenance"]["verification_status"].update(
            {"rule_refs": ["location-rule", "other-rule"]}
        ),
        lambda payload: payload["field_provenance"]["verification_status"].update(
            {"rule_refs": ["other-rule"]}
        ),
        lambda payload: payload.update({"source_refs": []}),
        lambda payload: payload.update({"data_origin": DataOrigin.DERIVED}),
        lambda payload: payload.update({"rule_refs": ["entity-rule"]}),
    ],
)
def test_field_provenance_adversarial_mutations_fail(mutation: object) -> None:
    import copy

    mutated = copy.deepcopy(mixed_record_payload())
    mutation(mutated)  # type: ignore[operator]
    with pytest.raises(ValidationError):
        CanonicalRecord.model_validate(mutated)


def test_duplicate_provenance_reference_ids_fail() -> None:
    with pytest.raises(ValidationError, match="duplicate source_record_id"):
        DerivedMetadata(
            data_origin=DataOrigin.DERIVED,
            source_record_ids=["record-1", "record-1"],
            transform_version="v1",
            function_name="normalize_record",
            input_checksum="b" * 64,
        )
    with pytest.raises(ValidationError, match="duplicate simulation reference ID"):
        SimulationMetadata(
            data_origin=DataOrigin.EVIDENCE_BACKED_SIMULATION,
            rule_ids=["rule-1", "rule-1"],
            evidence_ids=["evidence-1"],
            calibration_method="bounded_demo_value",
            allowed_values_or_range={"min": 1, "max": 5},
            unit="count",
            seed="demo-seed",
            confidence="medium",
            limitations=["not operational evidence"],
            generated_values={"value": 3},
        )


def test_bundle_rejects_naive_datetime() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        CanonicalBundleContent(
            bundle_version="v1",
            profile="realistic_demo",
            as_of=date(2026, 8, 9),
            timezone="Pacific/Auckland",
            seed="seed",
            expected_schema_revision="revision",
            source_checksums={},
            records=[
                CanonicalRecord(
                    entity_type="thing",
                    entity_id="thing-1",
                    attributes={"at": datetime(2026, 8, 9)},
                    data_origin=DataOrigin.DERIVED,
                    source_refs=["record-1"],
                    rule_refs=[],
                    field_provenance={
                        "entity_id": derived_field_provenance(),
                        "at": derived_field_provenance(),
                    },
                )
            ],
        )


def test_exact_simulation_coverage_matches_current_metadata() -> None:
    rules = json.loads(RULES_PATH.read_text())
    evidence = EvidenceRegister.model_validate(json.loads(EVIDENCE_PATH.read_text()))
    rule_set = type_from_rules(rules)
    result = validate_simulation_coverage(rule_set, Base.metadata, evidence)
    assert result.missing == ()
    assert result.extra == ()
    assert result.duplicate == ()
    assert result.target_count > 0


def type_from_rules(payload: dict[str, object]) -> object:
    from backend.app.etl.contracts import SimulationRuleSet

    return SimulationRuleSet.model_validate(payload)


def test_coverage_rejects_missing_duplicate_extra_unknown_table() -> None:
    import copy

    from backend.app.etl.contracts import SimulationRuleSet

    payload = json.loads(RULES_PATH.read_text())
    valid = SimulationRuleSet.model_validate(payload)
    evidence = EvidenceRegister.model_validate(json.loads(EVIDENCE_PATH.read_text()))

    missing_payload = copy.deepcopy(payload)
    missing_payload["rules"][0]["target_fields"].pop()
    with pytest.raises(ValueError, match="missing"):
        validate_simulation_coverage(
            SimulationRuleSet.model_validate(missing_payload), Base.metadata, evidence
        )

    duplicate_payload = copy.deepcopy(payload)
    duplicate_payload["rules"][1]["target_fields"].append(
        duplicate_payload["rules"][0]["target_fields"][0]
    )
    with pytest.raises(ValueError, match="duplicate"):
        validate_simulation_coverage(
            SimulationRuleSet.model_validate(duplicate_payload), Base.metadata, evidence
        )

    extra_payload = copy.deepcopy(payload)
    extra_payload["rules"][0]["target_fields"].append("users.not_a_column")
    with pytest.raises(ValueError, match="extra"):
        validate_simulation_coverage(
            SimulationRuleSet.model_validate(extra_payload), Base.metadata, evidence
        )

    unknown_payload = copy.deepcopy(payload)
    unknown_payload["scenario_tables"].append("not_a_table")
    with pytest.raises(ValueError, match="unknown table"):
        validate_simulation_coverage(
            SimulationRuleSet.model_validate(unknown_payload), Base.metadata, evidence
        )

    missing_evidence_payload = valid.model_copy(
        update={
            "rules": [
                valid.rules[0].model_copy(update={"evidence_ids": ["missing-evidence"]}),
                *valid.rules[1:],
            ]
        }
    )
    with pytest.raises(ValueError, match="missing-evidence"):
        validate_simulation_coverage(missing_evidence_payload, Base.metadata, evidence)
