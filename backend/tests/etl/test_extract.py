import json
import shutil
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from backend.app.etl import extract as extract_module
from backend.app.etl.extract import (
    ExtractionError,
    bounded_http_read,
    extract_source,
)

ROOT = Path(__file__).parents[3]
WOOLWORTHS_FIXTURE = ROOT / "backend/tests/etl/fixtures/woolworths-minimal.json"
MPI_FIXTURE = ROOT / "backend/tests/etl/fixtures/mpi-recalls-minimal.md"


def _response_handler(
    body: bytes,
    *,
    content_type: str | None = "application/json",
    status_code: int = 200,
    extra_headers: dict[str, str] | None = None,
):
    def handler(request: httpx.Request) -> httpx.Response:
        headers = dict(extra_headers or {})
        if content_type is not None:
            headers["content-type"] = content_type
        return httpx.Response(status_code, headers=headers, content=body, request=request)

    return handler


def test_bounded_fetch_accepts_redirects_and_missing_woolworths_mime_warning() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                302,
                headers={"location": "https://example.test/final"},
                request=request,
            )
        return httpx.Response(200, content=b"{}", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
        result = bounded_http_read(
            "https://example.test/start",
            max_snapshot_bytes=10,
            expected_content_type="application/json",
            timeout=1,
            client=client,
            allow_missing_content_type=True,
        )
    assert result.body == b"{}"
    assert result.status_code == 200
    assert result.content_type is None
    assert result.warnings == ("response is missing Content-Type",)
    assert calls == 2


def test_bounded_fetch_rejects_status_timeout_transport_declared_actual_and_mime_errors() -> None:
    with (
        httpx.Client(
            transport=httpx.MockTransport(_response_handler(b"no", status_code=503)),
            follow_redirects=True,
        ) as client,
        pytest.raises(ExtractionError, match="HTTP status 503"),
    ):
        bounded_http_read(
            "https://example.test/status",
            max_snapshot_bytes=10,
            expected_content_type="application/json",
            client=client,
        )

    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with (
        httpx.Client(transport=httpx.MockTransport(timeout_handler)) as client,
        pytest.raises(ExtractionError, match="transport failure"),
    ):
        bounded_http_read(
            "https://example.test/timeout",
            max_snapshot_bytes=10,
            expected_content_type="application/json",
            client=client,
        )

    def transport_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("unavailable", request=request)

    with (
        httpx.Client(transport=httpx.MockTransport(transport_handler)) as client,
        pytest.raises(ExtractionError, match="transport failure"),
    ):
        bounded_http_read(
            "https://example.test/transport",
            max_snapshot_bytes=10,
            expected_content_type="application/json",
            client=client,
        )

    with (
        httpx.Client(
            transport=httpx.MockTransport(
                _response_handler(
                    b"{}",
                    extra_headers={"content-length": "11"},
                )
            )
        ) as client,
        pytest.raises(ExtractionError, match="declared response size"),
    ):
        bounded_http_read(
            "https://example.test/declared",
            max_snapshot_bytes=10,
            expected_content_type="application/json",
            client=client,
        )

    with (
        httpx.Client(
            transport=httpx.MockTransport(
                _response_handler(b"123456", extra_headers={"content-length": "5"})
            )
        ) as client,
        pytest.raises(ExtractionError, match="actual response size"),
    ):
        bounded_http_read(
            "https://example.test/actual",
            max_snapshot_bytes=5,
            expected_content_type="application/json",
            client=client,
        )

    with (
        httpx.Client(
            transport=httpx.MockTransport(_response_handler(b"{}", content_type="text/plain"))
        ) as client,
        pytest.raises(ExtractionError, match="incompatible Content-Type"),
    ):
        bounded_http_read(
            "https://example.test/mime",
            max_snapshot_bytes=10,
            expected_content_type="application/json",
            client=client,
        )


def _isolated_repo(tmp_path: Path) -> Path:
    manifest_path = tmp_path / "data/etl/manifests/sources.v1.json"
    manifest_path.parent.mkdir(parents=True)
    shutil.copy(ROOT / "data/etl/manifests/sources.v1.json", manifest_path)
    return tmp_path


def _set_manifest_expected_count(repo: Path, source_id: str, expected_count: int) -> None:
    manifest_path = repo / "data/etl/manifests/sources.v1.json"
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    for source in document["sources"]:
        if source["source_id"] == source_id:
            source["expected_count"]["expected_count"] = expected_count
            break
    else:
        raise AssertionError(f"missing source {source_id}")
    manifest_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _local_clock() -> datetime:
    return datetime(2026, 8, 9, 12, tzinfo=timezone(timedelta(hours=12)))


def test_extract_creates_replays_and_rejects_raw_drift_without_overwrite(tmp_path: Path) -> None:
    repo = _isolated_repo(tmp_path)
    _set_manifest_expected_count(repo, "woolworths-store-locator", 2)
    body = WOOLWORTHS_FIXTURE.read_bytes()

    with httpx.Client(
        transport=httpx.MockTransport(_response_handler(body)),
        follow_redirects=True,
    ) as client:
        first = extract_source(
            "woolworths-store-locator", repo_root=repo, client=client, clock=_local_clock
        )
    raw_path = repo / first["raw_path"]
    records_path = repo / first["records_path"]
    report_path = raw_path.parent / "woolworths-store-locator.report.json"
    original_raw = raw_path.read_bytes()
    assert first["raw_checksum"]
    assert first["raw_bytes"] == len(body)
    assert first["drift"] == []
    assert first["source_last_reviewed"] is None
    assert b"retrieved_at" not in records_path.read_bytes()
    assert report_path.exists()
    assert list(raw_path.parent.glob(f".{raw_path.name}.*.tmp")) == []

    with httpx.Client(
        transport=httpx.MockTransport(_response_handler(body)),
        follow_redirects=True,
    ) as client:
        replay = extract_source(
            "woolworths-store-locator",
            repo_root=repo,
            client=client,
            clock=lambda: datetime(2030, 1, 1, tzinfo=UTC),
        )
    assert replay == first
    assert raw_path.read_bytes() == original_raw

    changed = body.replace(b"Twenty Woolworths", b"Changed Woolworths")
    with (
        httpx.Client(
            transport=httpx.MockTransport(_response_handler(changed)),
            follow_redirects=True,
        ) as client,
        pytest.raises(ExtractionError, match="raw drift"),
    ):
        extract_source(
            "woolworths-store-locator", repo_root=repo, client=client, clock=_local_clock
        )
    assert raw_path.read_bytes() == original_raw

    report_path.unlink()
    with (
        httpx.Client(
            transport=httpx.MockTransport(_response_handler(body)),
            follow_redirects=True,
        ) as client,
        pytest.raises(ExtractionError, match="partial artifact set"),
    ):
        extract_source(
            "woolworths-store-locator", repo_root=repo, client=client, clock=_local_clock
        )
    assert raw_path.read_bytes() == original_raw


def test_extract_rejects_woolworths_count_drift_before_any_artifact(tmp_path: Path) -> None:
    repo = _isolated_repo(tmp_path)
    body = WOOLWORTHS_FIXTURE.read_bytes()

    with (
        httpx.Client(
            transport=httpx.MockTransport(_response_handler(body)),
            follow_redirects=True,
        ) as client,
        pytest.raises(
            ExtractionError,
            match=r"woolworths source count drift: expected 61.*observed 2",
        ),
    ):
        extract_source(
            "woolworths-store-locator", repo_root=repo, client=client, clock=_local_clock
        )

    assert not (repo / "data/etl/raw").exists()


def test_extract_mpi_uses_jina_route_and_preserves_authority_attribution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _isolated_repo(tmp_path)
    _set_manifest_expected_count(repo, "mpi-recalled-products", 12)
    monkeypatch.setattr(
        extract_module,
        "EXPECTED_YEAR_COUNTS",
        dict.fromkeys(range(2016, 2027), 1) | {2022: 2},
    )
    body = MPI_FIXTURE.read_bytes()
    with httpx.Client(
        transport=httpx.MockTransport(_response_handler(body, content_type="text/plain")),
        follow_redirects=True,
    ) as client:
        report = extract_source(
            "mpi-recalled-products", repo_root=repo, client=client, clock=_local_clock
        )

    assert report["canonical_url"].startswith("https://www.mpi.govt.nz/")
    assert report["retrieval_url_used"].startswith("https://r.jina.ai/https://www.mpi.govt.nz/")
    assert report["retrieval_method"] == "jina_reader"
    assert report["observed_content_type"] == "text/plain"
    assert report["records_count"] == 12
    assert report["source_last_reviewed"] == "2026-07-23"
    assert (
        report["attribution"]["license_url"]
        == "https://www.mpi.govt.nz/about-this-site/mpi-copyright"
    )
    assert report["drift"] == []
    report_path = (repo / report["raw_path"]).parent / "mpi-recalled-products.report.json"
    assert list(report_path.parent.glob(f".{report_path.name}.*.tmp")) == []

    report_document = json.loads(report_path.read_text(encoding="utf-8"))
    report_document["source_last_reviewed"] = "2026-07-24"
    report_path.write_text(
        json.dumps(report_document, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )
    with (
        httpx.Client(
            transport=httpx.MockTransport(_response_handler(body, content_type="text/plain")),
            follow_redirects=True,
        ) as client,
        pytest.raises(ExtractionError, match="incoherent at 'source_last_reviewed'"),
    ):
        extract_source("mpi-recalled-products", repo_root=repo, client=client, clock=_local_clock)


def test_extract_rejects_mpi_aggregate_count_drift_before_any_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _isolated_repo(tmp_path)
    monkeypatch.setattr(
        extract_module,
        "EXPECTED_YEAR_COUNTS",
        dict.fromkeys(range(2016, 2027), 1) | {2022: 2},
    )
    body = MPI_FIXTURE.read_bytes()

    with (
        httpx.Client(
            transport=httpx.MockTransport(_response_handler(body, content_type="text/plain")),
            follow_redirects=True,
        ) as client,
        pytest.raises(
            ExtractionError,
            match=r"mpi source count drift: .*aggregate expected 660.*observed 12",
        ),
    ):
        extract_source("mpi-recalled-products", repo_root=repo, client=client, clock=_local_clock)

    assert not (repo / "data/etl/raw").exists()


def test_extract_rejects_mpi_per_year_count_drift_before_any_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _isolated_repo(tmp_path)
    _set_manifest_expected_count(repo, "mpi-recalled-products", 12)
    monkeypatch.setattr(
        extract_module,
        "EXPECTED_YEAR_COUNTS",
        dict.fromkeys(range(2016, 2027), 1) | {2016: 2, 2022: 2},
    )
    body = MPI_FIXTURE.read_bytes()

    with (
        httpx.Client(
            transport=httpx.MockTransport(_response_handler(body, content_type="text/plain")),
            follow_redirects=True,
        ) as client,
        pytest.raises(
            ExtractionError,
            match=r"mpi source count drift: .*year 2016 expected 2 records, observed 1",
        ),
    ):
        extract_source("mpi-recalled-products", repo_root=repo, client=client, clock=_local_clock)

    assert not (repo / "data/etl/raw").exists()


def test_extract_rejects_unknown_source_without_network_or_database() -> None:
    with pytest.raises(ExtractionError, match="unsupported Phase 1 source ID"):
        extract_source("not-a-known-source")
