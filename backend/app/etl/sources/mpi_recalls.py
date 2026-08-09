"""Pure parser for the MPI recalled-products Jina Reader Markdown snapshot."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime

CANONICAL_MPI_URL = (
    "https://www.mpi.govt.nz/food-safety-home/food-recalls-and-complaints/recalled-food-products"
)
CANONICAL_RECALL_PREFIX = f"{CANONICAL_MPI_URL}/"
LEGACY_RECALL_PREFIX = "https://www.mpi.govt.nz/food-safety/food-recalls/recalled-food-products/"
REQUIRED_YEAR_RANGE = range(2016, 2027)
EXPECTED_YEAR_COUNTS: dict[int, int] = {
    2016: 25,
    2017: 53,
    2018: 66,
    2019: 74,
    2020: 90,
    2021: 51,
    2022: 51,
    2023: 68,
    2024: 88,
    2025: 57,
    2026: 37,
}


class MpiRecallParseError(ValueError):
    """Raised when the MPI Reader snapshot is challenged or malformed."""


@dataclass(frozen=True, slots=True)
class MpiRecallParseResult:
    """Deterministic three-field records and dated count metadata."""

    records: tuple[dict[str, object], ...]
    year_counts: dict[int, int]
    before_count: int
    after_count: int
    filter_counts: dict[str, int]
    drift: tuple[str, ...]
    source_last_reviewed: date


_YEAR_HEADING = re.compile(r"^##\s+(20\d{2})\s+recalls\s*$")
_LEVEL_TWO_HEADING = re.compile(r"^##\s+(.+?)\s*$")
_MARKDOWN_LINK = re.compile(
    r"^\s*(?:[-*+]\s+|\d+[.)]\s+)\[([^\]]+)\]"
    r"\((https?://[^)\s]+)(?:\s+(?:\"[^\"]*\"|'[^']*'))?\)"
    r"(?:\[\]\(\2\))?\s*$"
)
_LAST_REVIEWED = re.compile(r"^\s*Last reviewed\s*:\s*(\d{2}\.\d{2}\.\d{2})\s*$", re.MULTILINE)


def _challenge_marker(text: str) -> str | None:
    folded = text.casefold()
    for marker in ("incapsula", "_incapsula_resource", "request unsuccessful"):
        if marker in folded:
            return marker
    if re.search(r"robots\s+noindex\s*,\s*nofollow", folded):
        return "robots noindex,nofollow"
    return None


def _required_reader_markers(text: str) -> date:
    if "Title: Recalled food products list | NZ Government" not in text:
        raise MpiRecallParseError("missing Jina Reader title marker")
    source_marker = f"URL Source: {CANONICAL_MPI_URL}"
    if source_marker not in text:
        raise MpiRecallParseError("missing canonical MPI URL Source marker")
    reviewed_values = _LAST_REVIEWED.findall(text)
    if not reviewed_values:
        raise MpiRecallParseError("missing MPI reviewed-date marker")
    reviewed_dates: list[date] = []
    for value in reviewed_values:
        try:
            reviewed_dates.append(datetime.strptime(value, "%d.%m.%y").date())
        except ValueError as exc:
            raise MpiRecallParseError(f"invalid MPI reviewed-date marker: {value}") from exc
    if len(set(reviewed_dates)) != 1:
        raise MpiRecallParseError("conflicting MPI reviewed-date markers")
    return reviewed_dates[0]


def _year_sections(text: str, as_of: date) -> dict[int, tuple[str, ...]]:
    lines = text.splitlines()
    all_headings: list[tuple[int, str]] = []
    year_headings: list[tuple[int, int]] = []
    for index, line in enumerate(lines):
        heading = _LEVEL_TWO_HEADING.match(line)
        if heading is None:
            continue
        heading_text = heading.group(1).strip()
        all_headings.append((index, heading_text))
        year_match = _YEAR_HEADING.match(line)
        if year_match is not None and int(year_match.group(1)) in REQUIRED_YEAR_RANGE:
            year_headings.append((index, int(year_match.group(1))))
    counts: dict[int, int] = {}
    for _, year in year_headings:
        counts[year] = counts.get(year, 0) + 1
    required_years = set(range(2016, as_of.year + 1))
    if set(counts) != required_years or any(count != 1 for count in counts.values()):
        missing = sorted(required_years - set(counts))
        duplicate = sorted(year for year, count in counts.items() if count > 1)
        raise MpiRecallParseError(
            "year sections must contain each year exactly once; "
            f"missing={missing}, duplicate={duplicate}"
        )

    result: dict[int, tuple[str, ...]] = {}
    for start, year in year_headings:
        end = next(
            (heading_index for heading_index, _ in all_headings if heading_index > start),
            len(lines),
        )
        result[year] = tuple(lines[start + 1 : end])
    return result


def _canonical_recall_url(url: str) -> bool:
    return any(url.startswith(prefix) for prefix in (CANONICAL_RECALL_PREFIX, LEGACY_RECALL_PREFIX))


def parse_mpi_recalled_products(
    payload: bytes,
    as_of: date,
    expected_year_counts: Mapping[int, int] | None = None,
) -> MpiRecallParseResult:
    """Parse only recall links inside the required year sections."""

    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MpiRecallParseError("Reader response is not valid UTF-8") from exc
    marker = _challenge_marker(text)
    if marker is not None:
        raise MpiRecallParseError(f"challenge/WAF marker detected: {marker}")
    source_last_reviewed = _required_reader_markers(text)
    sections = _year_sections(text, as_of)

    records: list[dict[str, object]] = []
    year_counts: dict[int, int] = {}
    for year in sorted(sections):
        seen_urls: set[str] = set()
        year_records: list[dict[str, object]] = []
        for line in sections[year]:
            match = _MARKDOWN_LINK.match(line)
            if match is None:
                continue
            title = match.group(1).strip()
            url = match.group(2).strip()
            if not title or not _canonical_recall_url(url):
                raise MpiRecallParseError(f"non-canonical recall link in {year}: {url}")
            if url in seen_urls:
                raise MpiRecallParseError(f"duplicate recall URL in {year}: {url}")
            seen_urls.add(url)
            year_records.append({"year": year, "title": title, "canonical_recall_url": url})
        year_records.sort(
            key=lambda record: (
                str(record["title"]).casefold(),
                str(record["title"]),
                str(record["canonical_recall_url"]),
            )
        )
        records.extend(year_records)
        year_counts[year] = len(year_records)

    drift: list[str] = []
    if expected_year_counts is not None:
        for year in sorted(expected_year_counts):
            observed = year_counts.get(year)
            if observed != expected_year_counts[year]:
                drift.append(
                    f"year {year} expected {expected_year_counts[year]} records, "
                    f"observed {observed}"
                )
    return MpiRecallParseResult(
        records=tuple(records),
        year_counts=year_counts,
        before_count=len(records),
        after_count=len(records),
        filter_counts={"year_sections": len(sections), "recall_links": len(records)},
        drift=tuple(drift),
        source_last_reviewed=source_last_reviewed,
    )
