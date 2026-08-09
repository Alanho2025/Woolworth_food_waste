"""Small, strict, side-effect-free contracts for the ETL control plane."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal
from urllib.parse import urlparse
from uuid import UUID, uuid5

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictStr,
    StringConstraints,
    field_validator,
    model_validator,
)
from sqlalchemy import MetaData

NonEmptyStr = Annotated[StrictStr, StringConstraints(strip_whitespace=True, min_length=1)]
JsonObject = dict[str, Any]


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DataOrigin(StrEnum):
    OBSERVED = "observed"
    DERIVED = "derived"
    EVIDENCE_BACKED_SIMULATION = "evidence_backed_simulation"
    UNKNOWN = "unknown"


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError("datetime must be timezone-aware")
    return value


class ObservedMetadata(_Contract):
    data_origin: Literal[DataOrigin.OBSERVED]
    source_id: NonEmptyStr
    snapshot_id: NonEmptyStr
    retrieved_at: datetime
    observed_at: datetime | None = None
    raw_reference: NonEmptyStr
    source_checksum: NonEmptyStr

    _validate_times = field_validator("retrieved_at", "observed_at")(_aware)


class DerivedMetadata(_Contract):
    data_origin: Literal[DataOrigin.DERIVED]
    source_record_ids: list[NonEmptyStr] = Field(min_length=1)
    transform_version: NonEmptyStr
    function_name: NonEmptyStr
    input_checksum: NonEmptyStr

    @field_validator("source_record_ids")
    @classmethod
    def source_record_ids_are_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("duplicate source_record_id")
        return value


class SimulationMetadata(_Contract):
    data_origin: Literal[DataOrigin.EVIDENCE_BACKED_SIMULATION]
    rule_ids: list[NonEmptyStr] = Field(min_length=1)
    evidence_ids: list[NonEmptyStr] = Field(min_length=1)
    calibration_method: NonEmptyStr
    allowed_values_or_range: Any
    unit: NonEmptyStr
    seed: NonEmptyStr
    confidence: Literal["high", "medium", "low"]
    limitations: list[NonEmptyStr] = Field(min_length=1)
    generated_values: Any

    @field_validator("rule_ids", "evidence_ids")
    @classmethod
    def reference_ids_are_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("duplicate simulation reference ID")
        return value


class UnknownMetadata(_Contract):
    data_origin: Literal[DataOrigin.UNKNOWN]
    reason: NonEmptyStr
    missing_evidence: list[NonEmptyStr] = Field(min_length=1)
    promotion_gate: NonEmptyStr


OriginMetadata = Annotated[
    ObservedMetadata | DerivedMetadata | SimulationMetadata | UnknownMetadata,
    Field(discriminator="data_origin"),
]


def _canonical_entity_key(entity_type: str, entity_id: str | UUID) -> tuple[str, str]:
    return entity_type, str(entity_id)


class CanonicalEntityRef(_Contract):
    entity_type: NonEmptyStr
    entity_id: NonEmptyStr | UUID
    data_origin: DataOrigin
    source_refs: list[NonEmptyStr]
    rule_refs: list[NonEmptyStr]

    @field_validator("source_refs", "rule_refs")
    @classmethod
    def references_are_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("duplicate entity reference")
        return value

    @model_validator(mode="after")
    def references_match_origin(self) -> CanonicalEntityRef:
        if self.data_origin in (DataOrigin.OBSERVED, DataOrigin.DERIVED):
            if not self.source_refs or self.rule_refs:
                raise ValueError("observed and derived entities require a source and no rule")
        elif self.data_origin is DataOrigin.EVIDENCE_BACKED_SIMULATION:
            if not self.rule_refs:
                raise ValueError("simulated entity requires at least one rule reference")
        elif self.source_refs or self.rule_refs:
            raise ValueError("unknown entity cannot reference sources or rules")
        return self


class ETLMetadata(_Contract):
    profile: NonEmptyStr
    bundle_id: NonEmptyStr | UUID
    origin_metadata: OriginMetadata
    canonical_entity_refs: list[CanonicalEntityRef]

    @model_validator(mode="after")
    def canonical_entity_refs_are_unique(self) -> ETLMetadata:
        keys = [
            _canonical_entity_key(ref.entity_type, ref.entity_id)
            for ref in self.canonical_entity_refs
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate canonical entity reference")
        return self


class RawPayloadEnvelope(_Contract):
    source_payload: JsonObject
    etl_metadata: ETLMetadata

    @model_validator(mode="after")
    def fail_closed(self) -> RawPayloadEnvelope:
        _validate_serialized_raw_payload(self)
        return self


SECRET_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "oauth_subject",
        "access_token",
        "refresh_token",
        "authorization",
        "cookie",
        "api_key",
        "secret",
    }
)


def _reject_secret_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if isinstance(key, str) and key.casefold() in SECRET_KEYS:
                raise ValueError(f"secret-like key is not allowed: {key}")
            _reject_secret_keys(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _reject_secret_keys(nested)


def _normalise_json(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return _normalise_json(value.value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetime must be timezone-aware")
        utc_value = value.astimezone(UTC).isoformat().replace("+00:00", "Z")
        return utc_value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Mapping):
        normalised: dict[str, Any] = {}
        for key, nested in value.items():
            if not isinstance(key, str):
                raise TypeError("JSON object keys must be strings")
            normalised[key] = _normalise_json(nested)
        return dict(sorted(normalised.items()))
    if isinstance(value, (list, tuple)):
        return [_normalise_json(nested) for nested in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite floats are not valid canonical JSON")
        return value
    raise TypeError(f"unsupported JSON value type: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _normalise_json(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _validate_serialized_raw_payload(envelope: RawPayloadEnvelope) -> bytes:
    payload_value = envelope.model_dump(mode="python")
    _reject_secret_keys(payload_value)
    payload = canonical_json_bytes(payload_value)
    if len(payload) > 65_536:
        raise ValueError("raw payload envelope exceeds 65,536 serialized bytes")
    return payload


def validate_raw_payload(envelope: RawPayloadEnvelope) -> bytes:
    """Return canonical bytes after rechecking the fail-closed envelope."""

    return _validate_serialized_raw_payload(envelope)


class CountAssertion(_Contract):
    expected_count: int = Field(strict=True, ge=0)
    as_of: date
    scope: NonEmptyStr


class SourceSpec(_Contract):
    source_id: NonEmptyStr
    source_kind: Literal[
        "http_json",
        "http_html",
        "http_markdown",
        "reviewed_json",
        "reviewed_csv",
    ]
    authority: NonEmptyStr
    url_or_path: NonEmptyStr
    retrieval_url: NonEmptyStr | None = None
    expected_content_type: NonEmptyStr
    max_snapshot_bytes: int = Field(strict=True, gt=0)
    scope: NonEmptyStr
    as_of: date
    license_note: NonEmptyStr
    expected_count: CountAssertion | None = None

    @model_validator(mode="after")
    def validate_urls_and_paths(self) -> SourceSpec:
        if self.source_kind.startswith("reviewed_"):
            path = self.url_or_path
            if (
                path.startswith(("/", "\\"))
                or "://" in path
                or any(part in ("", ".", "..") for part in path.replace("\\", "/").split("/"))
            ):
                raise ValueError("reviewed source paths must be repo-relative")
            if self.retrieval_url is not None:
                raise ValueError("reviewed sources cannot define a retrieval URL")
            return self

        for field_name, value in (
            ("url_or_path", self.url_or_path),
            ("retrieval_url", self.retrieval_url),
        ):
            if value is None:
                continue
            parsed = urlparse(value)
            if parsed.scheme != "https" or not parsed.netloc:
                raise ValueError(f"{field_name} must be an absolute HTTPS URL")
        return self


class SourceManifest(_Contract):
    version: NonEmptyStr
    as_of: date
    timezone: Literal["Pacific/Auckland"]
    sources: list[SourceSpec] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_source_ids(self) -> SourceManifest:
        ids = [source.source_id for source in self.sources]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate source_id")
        return self


class EvidenceEntry(_Contract):
    evidence_id: NonEmptyStr
    title: NonEmptyStr
    authority: NonEmptyStr
    url_or_repo_path: NonEmptyStr
    as_of: date
    supports: list[NonEmptyStr] = Field(min_length=1)
    does_not_support: list[NonEmptyStr] = Field(min_length=1)
    checked_at: datetime

    _validate_checked_at = field_validator("checked_at")(_aware)


class EvidenceRegister(_Contract):
    version: NonEmptyStr
    entries: list[EvidenceEntry] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_evidence_ids(self) -> EvidenceRegister:
        ids = [entry.evidence_id for entry in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate evidence_id")
        return self


class SimulationRule(_Contract):
    rule_id: NonEmptyStr
    target_fields: list[NonEmptyStr] = Field(min_length=1)
    evidence_ids: list[NonEmptyStr] = Field(min_length=1)
    calibration_method: NonEmptyStr
    allowed_values_or_range: Any
    unit: NonEmptyStr
    timezone: Literal["Pacific/Auckland"]
    confidence: Literal["high", "medium", "low"]
    limitations: list[NonEmptyStr] = Field(min_length=1)
    seed_namespace: NonEmptyStr
    version: NonEmptyStr

    @model_validator(mode="after")
    def reject_placeholder_text(self) -> SimulationRule:
        text = json.dumps(self.model_dump(mode="json"), ensure_ascii=False).casefold()
        for forbidden in ("tbd", "placeholder", "fallback"):
            if forbidden in text:
                raise ValueError(f"simulation rule contains forbidden {forbidden} text")
        return self

    @field_validator("target_fields", "evidence_ids")
    @classmethod
    def references_are_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("duplicate simulation rule reference")
        return value


class SimulationRuleSet(_Contract):
    version: NonEmptyStr
    scenario_tables: list[NonEmptyStr] = Field(min_length=1)
    rules: list[SimulationRule] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_rule_data(self) -> SimulationRuleSet:
        rule_ids = [rule.rule_id for rule in self.rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("duplicate rule_id")
        if len(self.scenario_tables) != len(set(self.scenario_tables)):
            raise ValueError("duplicate scenario table")
        return self


@dataclass(frozen=True)
class CoverageResult:
    target_count: int
    missing: tuple[str, ...]
    extra: tuple[str, ...]
    duplicate: tuple[str, ...]
    unknown_tables: tuple[str, ...]
    missing_evidence: tuple[str, ...]


def validate_simulation_coverage(
    rule_set: SimulationRuleSet,
    metadata: MetaData,
    evidence_register: EvidenceRegister | None = None,
) -> CoverageResult:
    unknown_tables = tuple(sorted(set(rule_set.scenario_tables) - set(metadata.tables)))
    expected: set[str] = set()
    for table_name in rule_set.scenario_tables:
        table = metadata.tables.get(table_name)
        if table is not None:
            expected.update(f"{table_name}.{column.name}" for column in table.columns)

    targets = [target for rule in rule_set.rules for target in rule.target_fields]
    target_counts = {target: targets.count(target) for target in set(targets)}
    duplicate = tuple(sorted(target for target, count in target_counts.items() if count > 1))
    target_set = set(targets)
    missing = tuple(sorted(expected - target_set))
    extra = tuple(sorted(target_set - expected))
    missing_evidence: tuple[str, ...] = ()
    if evidence_register is not None:
        evidence_ids = {entry.evidence_id for entry in evidence_register.entries}
        missing_evidence = tuple(
            sorted(
                {evidence_id for rule in rule_set.rules for evidence_id in rule.evidence_ids}
                - evidence_ids
            )
        )

    result = CoverageResult(
        target_count=len(expected),
        missing=missing,
        extra=extra,
        duplicate=duplicate,
        unknown_tables=unknown_tables,
        missing_evidence=missing_evidence,
    )
    problems: list[str] = []
    if unknown_tables:
        problems.append(f"unknown table: {', '.join(unknown_tables)}")
    if missing:
        problems.append(f"missing target fields: {', '.join(missing)}")
    if extra:
        problems.append(f"extra target fields: {', '.join(extra)}")
    if duplicate:
        problems.append(f"duplicate target owners: {', '.join(duplicate)}")
    if missing_evidence:
        problems.append(f"missing evidence IDs: {', '.join(missing_evidence)}")
    if problems:
        raise ValueError("; ".join(problems))
    return result


class DonorSelector(_Contract):
    source_key: NonEmptyStr
    region: Literal["AUK"]
    site_type: Literal["supermarket"]


class RecipientSelector(_Contract):
    current_public_relationship_evidence_required: Literal[True]
    protected_identity_allowed: Literal[False]
    public_coordinate_required: Literal[True]


class RouteTopology(_Contract):
    stops: list[Literal["pickup", "receiving"]]
    optimization_claim: Literal[False]

    @model_validator(mode="after")
    def pickup_then_receiving(self) -> RouteTopology:
        if self.stops != ["pickup", "receiving"]:
            raise ValueError("route topology must be pickup then receiving")
        return self


class ScenarioSelectors(_Contract):
    donor_store: DonorSelector
    recipient_site: RecipientSelector


class ScenarioConfig(_Contract):
    version: NonEmptyStr
    profile: Literal["realistic_demo"]
    as_of: date
    timezone: Literal["Pacific/Auckland"]
    seed_namespace: NonEmptyStr
    source_ids: list[NonEmptyStr] = Field(min_length=1)
    selectors: ScenarioSelectors
    required_cases: list[NonEmptyStr] = Field(min_length=1)
    route_topology: RouteTopology

    @field_validator("source_ids")
    @classmethod
    def source_ids_are_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("duplicate scenario source_id")
        return value


class FieldProvenance(_Contract):
    """Origin and references for one canonical entity or attribute field."""

    data_origin: DataOrigin
    origin_metadata: OriginMetadata
    source_refs: list[NonEmptyStr]
    rule_refs: list[NonEmptyStr]

    @field_validator("source_refs", "rule_refs")
    @classmethod
    def references_are_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("duplicate field provenance reference")
        return value

    @model_validator(mode="after")
    def references_match_origin(self) -> FieldProvenance:
        if self.origin_metadata.data_origin != self.data_origin:
            raise ValueError("field provenance origin does not match origin metadata")

        if isinstance(self.origin_metadata, ObservedMetadata):
            if self.source_refs != [self.origin_metadata.source_id] or self.rule_refs:
                raise ValueError("observed provenance requires its source and no rule")
        elif isinstance(self.origin_metadata, DerivedMetadata):
            if (
                set(self.source_refs) != set(self.origin_metadata.source_record_ids)
                or self.rule_refs
            ):
                raise ValueError("derived provenance requires its source records and no rule")
        elif isinstance(self.origin_metadata, SimulationMetadata):
            if (
                len(self.origin_metadata.rule_ids) != 1
                or len(self.rule_refs) != 1
                or self.rule_refs[0] != self.origin_metadata.rule_ids[0]
            ):
                raise ValueError("simulated provenance requires exactly one matching rule owner")
        elif self.source_refs or self.rule_refs:
            raise ValueError("unknown provenance cannot reference sources or rules")
        return self


class CanonicalRecord(_Contract):
    entity_type: NonEmptyStr
    entity_id: NonEmptyStr | UUID
    attributes: JsonObject
    data_origin: DataOrigin
    source_refs: list[NonEmptyStr]
    rule_refs: list[NonEmptyStr]
    field_provenance: dict[NonEmptyStr, FieldProvenance]

    @field_validator("source_refs", "rule_refs")
    @classmethod
    def references_are_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("duplicate canonical record reference")
        return value

    @model_validator(mode="after")
    def validate_provenance_and_attribute_values(self) -> CanonicalRecord:
        if "entity_id" in self.attributes:
            raise ValueError("attributes cannot contain reserved entity_id provenance key")
        expected_fields = {"entity_id", *self.attributes}
        actual_fields = set(self.field_provenance)
        missing = sorted(expected_fields - actual_fields)
        extra = sorted(actual_fields - expected_fields)
        if missing or extra:
            raise ValueError(
                "field provenance keys must exactly cover record fields; "
                f"missing={missing} extra={extra}"
            )
        identity = self.field_provenance["entity_id"]
        if (
            self.data_origin != identity.data_origin
            or self.source_refs != identity.source_refs
            or self.rule_refs != identity.rule_refs
        ):
            raise ValueError("record-level provenance contradicts entity identity provenance")
        for field_name, provenance in self.field_provenance.items():
            actual_value = (
                self.entity_id if field_name == "entity_id" else self.attributes[field_name]
            )
            if isinstance(provenance.origin_metadata, SimulationMetadata):
                generated_value = provenance.origin_metadata.generated_values
                if canonical_json_bytes(generated_value) != canonical_json_bytes(actual_value):
                    raise ValueError(
                        f"simulated generated value does not match field: {field_name}"
                    )
            elif isinstance(provenance.origin_metadata, UnknownMetadata) and not (
                actual_value is None
                or (isinstance(actual_value, str) and actual_value == "unknown")
            ):
                raise ValueError(f"unknown field has concrete value: {field_name}")
        _normalise_json(self.entity_id)
        _normalise_json(self.attributes)
        return self


class CanonicalBundleContent(_Contract):
    bundle_version: NonEmptyStr
    profile: NonEmptyStr
    as_of: date
    timezone: Literal["Pacific/Auckland"]
    seed: NonEmptyStr
    expected_schema_revision: NonEmptyStr
    source_checksums: dict[NonEmptyStr, NonEmptyStr]
    records: list[CanonicalRecord]

    @model_validator(mode="after")
    def canonical_entity_keys_are_unique(self) -> CanonicalBundleContent:
        keys = [
            _canonical_entity_key(record.entity_type, record.entity_id) for record in self.records
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate canonical entity key")
        return self


PROJECT_BUNDLE_NAMESPACE = UUID("8d6059a1-0e0f-5b18-b4c0-5d04e54b6f3f")


def bundle_content_checksum(content: CanonicalBundleContent) -> str:
    payload = content.model_dump(mode="python")
    records = payload["records"]
    payload["records"] = sorted(
        records,
        key=lambda record: (record["entity_type"], str(record["entity_id"])),
    )
    import hashlib

    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def deterministic_bundle_id(content: CanonicalBundleContent) -> UUID:
    identity = "|".join(
        (
            content.bundle_version,
            content.profile,
            content.as_of.isoformat(),
            content.timezone,
            content.seed,
            content.expected_schema_revision,
            bundle_content_checksum(content),
        )
    )
    return uuid5(PROJECT_BUNDLE_NAMESPACE, identity)


class BundleEnvelope(_Contract):
    bundle_id: UUID
    content: CanonicalBundleContent
    content_checksum: NonEmptyStr

    @model_validator(mode="after")
    def checksum_matches(self) -> BundleEnvelope:
        expected_checksum = bundle_content_checksum(self.content)
        if self.content_checksum != expected_checksum:
            raise ValueError("bundle content checksum mismatch")
        if self.bundle_id != deterministic_bundle_id(self.content):
            raise ValueError("bundle ID mismatch")
        return self
