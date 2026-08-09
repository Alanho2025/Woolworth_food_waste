"""Local-only loading and cross-reference checks for ETL control files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy import MetaData

from backend.app.etl.contracts import (
    CoverageResult,
    EvidenceRegister,
    ScenarioConfig,
    SimulationRuleSet,
    SourceManifest,
    canonical_json_bytes,
    validate_simulation_coverage,
)
from backend.app.models import Base


class ControlChecksum(tuple[str, str]):
    """Immutable `(relative path, sha256)` pair."""

    __slots__ = ()

    def __new__(cls, path: str, checksum: str) -> ControlChecksum:
        return tuple.__new__(cls, (path, checksum))

    @property
    def path(self) -> str:
        return self[0]

    @property
    def checksum(self) -> str:
        return self[1]


class ControlPlane:
    """Immutable aggregate of validated control contracts and checksums."""

    __slots__ = (
        "_sealed",
        "content_checksums",
        "coverage",
        "evidence_register",
        "file_checksums",
        "scenario_config",
        "simulation_rule_set",
        "source_manifest",
    )

    def __init__(
        self,
        source_manifest: SourceManifest,
        evidence_register: EvidenceRegister,
        simulation_rule_set: SimulationRuleSet,
        scenario_config: ScenarioConfig,
        file_checksums: tuple[ControlChecksum, ...],
        content_checksums: tuple[ControlChecksum, ...],
        coverage: CoverageResult,
    ) -> None:
        object.__setattr__(self, "source_manifest", source_manifest)
        object.__setattr__(self, "evidence_register", evidence_register)
        object.__setattr__(self, "simulation_rule_set", simulation_rule_set)
        object.__setattr__(self, "scenario_config", scenario_config)
        object.__setattr__(self, "file_checksums", file_checksums)
        object.__setattr__(self, "content_checksums", content_checksums)
        object.__setattr__(self, "coverage", coverage)
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("ControlPlane is immutable")
        object.__setattr__(self, name, value)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: unable to read valid JSON: {exc}") from exc


def load_source_manifest(path: str | Path) -> SourceManifest:
    path = Path(path)
    try:
        return SourceManifest.model_validate(_read_json(path))
    except (ValidationError, ValueError) as exc:
        raise ValueError(f"{path}: invalid source manifest: {exc}") from exc


def load_evidence_register(path: str | Path) -> EvidenceRegister:
    path = Path(path)
    try:
        return EvidenceRegister.model_validate(_read_json(path))
    except (ValidationError, ValueError) as exc:
        raise ValueError(f"{path}: invalid evidence register: {exc}") from exc


def load_simulation_rule_set(path: str | Path) -> SimulationRuleSet:
    path = Path(path)
    try:
        return SimulationRuleSet.model_validate(_read_json(path))
    except (ValidationError, ValueError) as exc:
        raise ValueError(f"{path}: invalid simulation rule set: {exc}") from exc


def load_scenario_config(path: str | Path) -> ScenarioConfig:
    path = Path(path)
    try:
        return ScenarioConfig.model_validate(_read_json(path))
    except (ValidationError, ValueError) as exc:
        raise ValueError(f"{path}: invalid scenario config: {exc}") from exc


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _contract_checksum(value: object) -> str:
    if not hasattr(value, "model_dump"):
        raise TypeError("control contract must be a Pydantic model")
    return _sha256_bytes(canonical_json_bytes(value.model_dump(mode="python")))


def load_control_plane(repo_root: str | Path, metadata: MetaData = Base.metadata) -> ControlPlane:
    root = Path(repo_root)
    paths = {
        "sources": root / "data/etl/manifests/sources.v1.json",
        "evidence": root / "data/etl/evidence/evidence-register.v1.json",
        "rules": root / "data/etl/rules/simulation-rules.v1.json",
        "scenario": root / "data/etl/reference/demo-scenario.v1.json",
    }
    source_manifest = load_source_manifest(paths["sources"])
    evidence_register = load_evidence_register(paths["evidence"])
    rule_set = load_simulation_rule_set(paths["rules"])
    scenario = load_scenario_config(paths["scenario"])

    source_ids = {source.source_id for source in source_manifest.sources}
    unresolved_sources = sorted(set(scenario.source_ids) - source_ids)
    if unresolved_sources:
        raise ValueError(
            f"{paths['scenario']}: unresolved source IDs: {', '.join(unresolved_sources)}"
        )

    coverage = validate_simulation_coverage(rule_set, metadata, evidence_register)
    relative_paths = {
        "sources": "data/etl/manifests/sources.v1.json",
        "evidence": "data/etl/evidence/evidence-register.v1.json",
        "rules": "data/etl/rules/simulation-rules.v1.json",
        "scenario": "data/etl/reference/demo-scenario.v1.json",
    }
    file_checksums = tuple(
        ControlChecksum(relative_paths[key], _sha256_bytes(paths[key].read_bytes()))
        for key in ("sources", "evidence", "rules", "scenario")
    )
    parsed = {
        "sources": source_manifest,
        "evidence": evidence_register,
        "rules": rule_set,
        "scenario": scenario,
    }
    content_checksums = tuple(
        ControlChecksum(relative_paths[key], _contract_checksum(parsed[key]))
        for key in ("sources", "evidence", "rules", "scenario")
    )
    return ControlPlane(
        source_manifest=source_manifest,
        evidence_register=evidence_register,
        simulation_rule_set=rule_set,
        scenario_config=scenario,
        file_checksums=file_checksums,
        content_checksums=content_checksums,
        coverage=coverage,
    )
