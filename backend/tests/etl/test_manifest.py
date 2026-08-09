import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.app.etl.contracts import SourceSpec
from backend.app.etl.manifest import (
    load_control_plane,
    load_scenario_config,
    load_source_manifest,
)
from backend.app.models import Base

ROOT = Path(__file__).parents[3]


def test_all_control_files_load_and_resolve_against_metadata() -> None:
    plane = load_control_plane(ROOT)
    assert len(plane.source_manifest.sources) == 5
    assert len(plane.evidence_register.entries) >= 10
    assert len(plane.simulation_rule_set.rules) > 0
    assert plane.coverage.target_count == sum(
        len(Base.metadata.tables[table].columns)
        for table in plane.simulation_rule_set.scenario_tables
    )
    assert plane.coverage.missing == ()
    assert plane.coverage.extra == ()
    assert plane.coverage.duplicate == ()


def test_loaders_include_path_for_malformed_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not-json")
    with pytest.raises(ValueError, match=str(bad)):
        load_source_manifest(bad)


def test_control_models_reject_extra_keys_and_duplicate_ids(tmp_path: Path) -> None:
    source_path = ROOT / "data/etl/manifests/sources.v1.json"
    source_payload = json.loads(source_path.read_text())
    source_payload["unexpected"] = True
    extra_path = tmp_path / "extra.json"
    extra_path.write_text(json.dumps(source_payload))
    with pytest.raises(ValueError, match=str(extra_path)):
        load_source_manifest(extra_path)

    duplicate_payload = json.loads(source_path.read_text())
    duplicate_payload["sources"].append(duplicate_payload["sources"][0])
    duplicate_path = tmp_path / "duplicate.json"
    duplicate_path.write_text(json.dumps(duplicate_payload))
    with pytest.raises(ValueError, match="duplicate"):
        load_source_manifest(duplicate_path)


def test_expected_counts_are_dated_review_assertions() -> None:
    manifest = load_source_manifest(ROOT / "data/etl/manifests/sources.v1.json")
    store = next(
        source for source in manifest.sources if source.source_id == "woolworths-store-locator"
    )
    assert store.expected_count is not None
    assert store.expected_count.expected_count == 61
    assert store.expected_count.as_of.isoformat() == "2026-08-09"
    assert store.expected_count.scope == "Auckland region stores after AUK filter"
    assert not hasattr(store, "parser_count")


def test_scenario_rejects_generated_values_key(tmp_path: Path) -> None:
    payload = json.loads((ROOT / "data/etl/reference/demo-scenario.v1.json").read_text())
    payload["generated_values"] = {"user_id": "must-not-be-here"}
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match=str(path)):
        load_scenario_config(path)


def test_execution_brief_declares_exact_governance_scope() -> None:
    brief = (ROOT / "docs/etl/execution-briefs/phase-0-attempt-1.md").read_text()
    for required in (
        "backend/app/etl/contracts.py",
        "data/etl/rules/simulation-rules.v1.json",
        "Everything else is forbidden",
        "All eleven allowed files",
        "docs/evidence-backed-etl-plan-xml.md",
        "Do not integrate this snapshot",
    ):
        assert required in brief


def test_phase1_manifest_separates_mpi_authority_and_reader_retrieval() -> None:
    manifest = load_source_manifest(ROOT / "data/etl/manifests/sources.v1.json")
    mpi = next(source for source in manifest.sources if source.source_id == "mpi-recalled-products")
    assert mpi.source_kind == "http_markdown"
    assert mpi.url_or_path == (
        "https://www.mpi.govt.nz/food-safety-home/food-recalls-and-complaints/"
        "recalled-food-products"
    )
    assert mpi.retrieval_url == (
        "https://r.jina.ai/https://www.mpi.govt.nz/food-safety-home/food-recalls-and-complaints/"
        "recalled-food-products"
    )
    assert mpi.expected_content_type == "text/plain"
    assert mpi.expected_count is not None
    assert mpi.expected_count.expected_count == 660


@pytest.mark.parametrize(
    ("source_kind", "url_or_path", "retrieval_url"),
    [
        ("reviewed_json", "/absolute.json", None),
        ("reviewed_json", "data/../secret.json", None),
        ("http_json", "http://example.test/source.json", None),
        ("http_json", "https://example.test/source.json", "http://example.test/read"),
    ],
)
def test_source_spec_rejects_unbounded_reviewed_paths_and_http_urls(
    source_kind: str, url_or_path: str, retrieval_url: str | None
) -> None:
    with pytest.raises(ValidationError):
        SourceSpec(
            source_id="test-source",
            source_kind=source_kind,
            authority="test authority",
            url_or_path=url_or_path,
            retrieval_url=retrieval_url,
            expected_content_type="application/json",
            max_snapshot_bytes=10,
            scope="test scope",
            as_of=date(2026, 8, 9),
            license_note="test note",
        )


def test_phase1_execution_brief_contains_phase_only_contract() -> None:
    brief = (ROOT / "docs/etl/execution-briefs/phase-1-attempt-1.md").read_text()
    for required in (
        "AC-04",
        "AC-09",
        "AC-10",
        "AC-13",
        "AC-14",
        "Locator.storelist[*].storeDetail",
        "Everything else is forbidden",
        "docs/evidence-backed-etl-plan-xml.md",
        "No database engine/session",
        "Corrections (append-only)",
    ):
        assert required in brief
    assert "/data/etl/raw/" in (ROOT / ".gitignore").read_text()
