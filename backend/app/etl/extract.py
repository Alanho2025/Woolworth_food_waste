"""Bounded, immutable Phase 1 extraction for the two explicit HTTP sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from backend.app.etl.contracts import SourceSpec, canonical_json_bytes
from backend.app.etl.manifest import load_source_manifest
from backend.app.etl.sources.mpi_recalls import (
    EXPECTED_YEAR_COUNTS,
    MpiRecallParseError,
    parse_mpi_recalled_products,
)
from backend.app.etl.sources.woolworths import (
    WoolworthsParseError,
    parse_woolworths_store_locator,
)

WoolworthsSourceId = "woolworths-store-locator"
MpiSourceId = "mpi-recalled-products"
KNOWN_HTTP_SOURCE_IDS = frozenset({WoolworthsSourceId, MpiSourceId})
RAW_EXTENSIONS = {WoolworthsSourceId: ".json", MpiSourceId: ".md"}
DEFAULT_TIMEOUT_SECONDS = 30.0


class ExtractionError(RuntimeError):
    """Raised when acquisition or immutable artifact handling fails."""


@dataclass(frozen=True, slots=True)
class FetchResult:
    body: bytes
    status_code: int
    content_type: str | None
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArtifactPaths:
    raw: Path
    records: Path
    report: Path


@dataclass(frozen=True, slots=True)
class PersistedArtifacts:
    report: dict[str, Any]
    reused: bool


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _media_type(value: str) -> str:
    return value.split(";", 1)[0].strip().casefold()


def _read_response(
    client: httpx.Client,
    url: str,
    max_snapshot_bytes: int,
    expected_content_type: str,
    timeout: float,
    allow_missing_content_type: bool,
) -> FetchResult:
    try:
        response_context = client.stream("GET", url, follow_redirects=True, timeout=timeout)
        with response_context as response:
            if not 200 <= response.status_code < 300:
                raise ExtractionError(f"HTTP status {response.status_code} is not successful")

            content_length = response.headers.get("content-length")
            if content_length is not None:
                try:
                    declared_length = int(content_length)
                except ValueError as exc:
                    raise ExtractionError("invalid Content-Length header") from exc
                if declared_length < 0:
                    raise ExtractionError("negative Content-Length header")
                if declared_length > max_snapshot_bytes:
                    raise ExtractionError(
                        f"declared response size {declared_length} exceeds "
                        f"{max_snapshot_bytes} bytes"
                    )

            content_type_header = response.headers.get("content-type")
            content_type = content_type_header.strip() if content_type_header else None
            warnings: tuple[str, ...] = ()
            if content_type is None:
                if not allow_missing_content_type:
                    raise ExtractionError("response is missing Content-Type")
                warnings = ("response is missing Content-Type",)
            elif _media_type(content_type) != _media_type(expected_content_type):
                raise ExtractionError(
                    f"incompatible Content-Type {content_type!r}; "
                    f"expected {_media_type(expected_content_type)!r}"
                )

            chunks: list[bytes] = []
            received = 0
            for chunk in response.iter_bytes():
                received += len(chunk)
                if received > max_snapshot_bytes:
                    raise ExtractionError(
                        f"actual response size exceeds {max_snapshot_bytes} bytes"
                    )
                chunks.append(chunk)
            return FetchResult(b"".join(chunks), response.status_code, content_type, warnings)
    except ExtractionError:
        raise
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise ExtractionError(f"HTTP transport failure: {exc}") from exc


def bounded_http_read(
    url: str,
    *,
    max_snapshot_bytes: int,
    expected_content_type: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    client: httpx.Client | None = None,
    allow_missing_content_type: bool = False,
) -> FetchResult:
    """Read one response with declared and actual byte ceilings."""

    if max_snapshot_bytes <= 0:
        raise ValueError("max_snapshot_bytes must be positive")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if client is not None:
        return _read_response(
            client,
            url,
            max_snapshot_bytes,
            expected_content_type,
            timeout,
            allow_missing_content_type,
        )
    with httpx.Client(timeout=timeout, follow_redirects=True) as owned_client:
        return _read_response(
            owned_client,
            url,
            max_snapshot_bytes,
            expected_content_type,
            timeout,
            allow_missing_content_type,
        )


def _artifact_paths(repo_root: Path, source: SourceSpec) -> ArtifactPaths:
    try:
        extension = RAW_EXTENSIONS[source.source_id]
    except KeyError as exc:
        raise ExtractionError(f"no raw extension configured for {source.source_id}") from exc
    directory = repo_root / "data/etl/raw" / source.as_of.isoformat()
    stem = directory / source.source_id
    return ArtifactPaths(
        raw=stem.with_suffix(extension),
        records=directory / f"{source.source_id}.records.json",
        report=directory / f"{source.source_id}.report.json",
    )


def _relative_path(repo_root: Path, path: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def _exclusive_write(path: Path, payload: bytes) -> None:
    temporary_path: Path | None = None
    try:
        file_descriptor, temporary_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(file_descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary_path, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except FileExistsError as exc:
        raise ExtractionError(f"cannot create immutable artifact {path}: {exc}") from exc
    except OSError as exc:
        raise ExtractionError(f"cannot create immutable artifact {path}: {exc}") from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
            except OSError as exc:
                raise ExtractionError(
                    f"cannot remove temporary artifact {temporary_path}: {exc}"
                ) from exc


def _read_existing_report(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExtractionError(f"existing report is not valid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ExtractionError(f"existing report must be a JSON object: {path}")
    return value


def _validate_existing_report(
    existing: Mapping[str, Any], expected: Mapping[str, Any], raw: bytes, records: bytes
) -> dict[str, Any]:
    immutable_keys = (
        "source_id",
        "canonical_url",
        "retrieval_url_used",
        "retrieval_method",
        "manifest",
        "http_status",
        "observed_content_type",
        "raw_path",
        "raw_checksum",
        "raw_bytes",
        "records_path",
        "records_checksum",
        "records_count",
        "before_count",
        "after_count",
        "filter_counts",
        "warnings",
        "drift",
        "source_last_reviewed",
        "source_limitations",
        "attribution",
    )
    for key in immutable_keys:
        if existing.get(key) != expected.get(key):
            raise ExtractionError(f"existing report is incoherent at {key!r}")
    if existing.get("raw_checksum") != _sha256(raw) or existing.get("raw_bytes") != len(raw):
        raise ExtractionError("existing report does not describe the existing raw bytes")
    if existing.get("records_checksum") != _sha256(records):
        raise ExtractionError("existing report does not describe the existing records")
    retrieved_at = existing.get("retrieved_at")
    if not isinstance(retrieved_at, str):
        raise ExtractionError("existing report has no retrieved_at timestamp")
    try:
        parsed_timestamp = datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExtractionError("existing report retrieved_at is not ISO datetime") from exc
    if parsed_timestamp.tzinfo is None or parsed_timestamp.utcoffset() is None:
        raise ExtractionError("existing report retrieved_at is not timezone-aware")
    return dict(existing)


def persist_artifacts(
    *,
    paths: ArtifactPaths,
    raw: bytes,
    records: bytes,
    report: dict[str, Any],
) -> PersistedArtifacts:
    """Create or reuse one coherent immutable raw/records/report set."""

    paths.raw.parent.mkdir(parents=True, exist_ok=True)
    exists = tuple(path.exists() for path in (paths.raw, paths.records, paths.report))
    if any(exists):
        if not all(exists):
            raise ExtractionError("partial artifact set exists; refusing to invent metadata")
        try:
            existing_raw = paths.raw.read_bytes()
            existing_records = paths.records.read_bytes()
        except OSError as exc:
            raise ExtractionError(f"cannot read existing artifact set: {exc}") from exc
        if existing_raw != raw:
            raise ExtractionError(
                f"raw drift at immutable path {paths.raw}; existing bytes preserved"
            )
        if existing_records != records:
            raise ExtractionError("existing records artifact is incoherent with the raw bytes")
        existing_report = _read_existing_report(paths.report)
        return PersistedArtifacts(
            report=_validate_existing_report(existing_report, report, raw, records),
            reused=True,
        )

    report_bytes = canonical_json_bytes(report)
    _exclusive_write(paths.raw, raw)
    _exclusive_write(paths.records, records)
    _exclusive_write(paths.report, report_bytes)
    return PersistedArtifacts(report=report, reused=False)


def _clock_timestamp(clock: Callable[[], datetime]) -> str:
    value = clock()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExtractionError("clock must return a timezone-aware datetime")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _source_limitations(source_id: str) -> tuple[str, ...]:
    if source_id == WoolworthsSourceId:
        return (
            "Store coordinates are public source centroids, not loading bays, entrances, or "
            "parking.",
            "The source snapshot does not establish donation participation or current "
            "store operations.",
        )
    return (
        "Jina Reader content is a text conversion of the supplied authority URL, not direct "
        "MPI HTML.",
        "Absence from this index is not product-safety evidence and does not cover future "
        "changes or other registers.",
        "Phase 1 performs no recall matching and cannot establish not_recalled for a product.",
    )


def _mpi_attribution() -> dict[str, object]:
    return {
        "authority": "New Zealand Ministry for Primary Industries",
        "license": "MPI website content is CC BY 4.0 with Crown attribution, except "
        "third-party material.",
        "license_url": "https://www.mpi.govt.nz/about-this-site/mpi-copyright",
        "limitation": "Third-party material may have separate rights and is not covered by "
        "MPI's licence.",
    }


def _expected_count(source: SourceSpec) -> int | None:
    return source.expected_count.expected_count if source.expected_count is not None else None


def _build_report(
    *,
    repo_root: Path,
    source: SourceSpec,
    fetch: FetchResult,
    retrieved_at: str,
    records: tuple[dict[str, object], ...],
    before_count: int,
    after_count: int,
    filter_counts: Mapping[str, int],
    warnings: tuple[str, ...],
    drift: tuple[str, ...],
    source_last_reviewed: str | None,
    retrieval_method: str,
    attribution: dict[str, object] | None,
) -> tuple[dict[str, Any], bytes, ArtifactPaths]:
    paths = _artifact_paths(repo_root, source)
    records_bytes = canonical_json_bytes(records)
    report: dict[str, Any] = {
        "source_id": source.source_id,
        "canonical_url": source.url_or_path,
        "retrieval_url_used": source.retrieval_url or source.url_or_path,
        "retrieval_method": retrieval_method,
        "manifest": {"as_of": source.as_of.isoformat(), "timezone": "Pacific/Auckland"},
        "retrieved_at": retrieved_at,
        "http_status": fetch.status_code,
        "observed_content_type": fetch.content_type,
        "raw_path": _relative_path(repo_root, paths.raw),
        "raw_checksum": _sha256(fetch.body),
        "raw_bytes": len(fetch.body),
        "records_path": _relative_path(repo_root, paths.records),
        "records_checksum": _sha256(records_bytes),
        "records_count": len(records),
        "before_count": before_count,
        "after_count": after_count,
        "filter_counts": dict(filter_counts),
        "warnings": list(warnings),
        "drift": list(drift),
        "source_last_reviewed": source_last_reviewed,
        "source_limitations": list(_source_limitations(source.source_id)),
        "attribution": attribution,
    }
    return report, records_bytes, paths


def extract_source(
    source_id: str,
    *,
    repo_root: str | Path = ".",
    client: httpx.Client | None = None,
    clock: Callable[[], datetime] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Extract one known source and return its coherent report."""

    root = Path(repo_root).resolve()
    if source_id not in KNOWN_HTTP_SOURCE_IDS:
        raise ExtractionError(f"unsupported Phase 1 source ID: {source_id}")
    manifest = load_source_manifest(root / "data/etl/manifests/sources.v1.json")
    source = next((item for item in manifest.sources if item.source_id == source_id), None)
    if source is None:
        raise ExtractionError(f"source ID is not present in the manifest: {source_id}")

    fetch = bounded_http_read(
        source.retrieval_url or source.url_or_path,
        max_snapshot_bytes=source.max_snapshot_bytes,
        expected_content_type=source.expected_content_type,
        timeout=timeout,
        client=client,
        allow_missing_content_type=source_id == WoolworthsSourceId,
    )
    warnings = fetch.warnings
    if source_id == WoolworthsSourceId:
        try:
            parsed = parse_woolworths_store_locator(fetch.body, _expected_count(source))
        except WoolworthsParseError as exc:
            raise ExtractionError(str(exc)) from exc
        records = parsed.records
        before_count = parsed.before_count
        after_count = parsed.division_count
        filter_counts = parsed.filter_counts
        drift = parsed.drift
        if drift:
            raise ExtractionError(f"woolworths source count drift: {'; '.join(drift)}")
        source_last_reviewed = None
        retrieval_method = "http"
        attribution = None
    else:
        try:
            parsed_mpi = parse_mpi_recalled_products(
                fetch.body,
                source.as_of,
                expected_year_counts=EXPECTED_YEAR_COUNTS,
            )
        except MpiRecallParseError as exc:
            raise ExtractionError(str(exc)) from exc
        records = parsed_mpi.records
        before_count = parsed_mpi.before_count
        after_count = parsed_mpi.after_count
        filter_counts = {
            **parsed_mpi.filter_counts,
            **{f"year_{year}": count for year, count in parsed_mpi.year_counts.items()},
        }
        drift_items = list(parsed_mpi.drift)
        expected_count = _expected_count(source)
        if expected_count is not None and len(records) != expected_count:
            drift_items.append(
                f"aggregate expected {expected_count} recall records, observed {len(records)}"
            )
        if drift_items:
            raise ExtractionError(f"mpi source count drift: {'; '.join(drift_items)}")
        drift = ()
        source_last_reviewed = parsed_mpi.source_last_reviewed.isoformat()
        retrieval_method = "jina_reader"
        attribution = _mpi_attribution()

    report, records_bytes, paths = _build_report(
        repo_root=root,
        source=source,
        fetch=fetch,
        retrieved_at=_clock_timestamp(clock or (lambda: datetime.now(UTC))),
        records=records,
        before_count=before_count,
        after_count=after_count,
        filter_counts=filter_counts,
        warnings=warnings,
        drift=drift,
        source_last_reviewed=source_last_reviewed,
        retrieval_method=retrieval_method,
        attribution=attribution,
    )
    return persist_artifacts(
        paths=paths, raw=fetch.body, records=records_bytes, report=report
    ).report


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract one Phase 1 real source")
    parser.add_argument("--source", required=True, choices=sorted(KNOWN_HTTP_SOURCE_IDS))
    parser.add_argument("--repo-root", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _argument_parser().parse_args(argv)
    try:
        report = extract_source(args.source, repo_root=args.repo_root)
    except (ExtractionError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 1
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
