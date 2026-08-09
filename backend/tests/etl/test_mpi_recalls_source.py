from datetime import date
from pathlib import Path

import pytest

from backend.app.etl.sources.mpi_recalls import (
    MpiRecallParseError,
    parse_mpi_recalled_products,
)

FIXTURE = Path(__file__).parent / "fixtures/mpi-recalls-minimal.md"


def fixture_text() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_mpi_reader_markdown_parses_required_years_and_allows_cross_year_url_reuse() -> None:
    parsed = parse_mpi_recalled_products(fixture_text().encode("utf-8"), date(2026, 8, 9))

    assert len(parsed.records) == 12
    assert set(parsed.year_counts) == set(range(2016, 2027))
    assert parsed.year_counts[2022] == 2
    assert parsed.year_counts[2023] == 1
    assert parsed.source_last_reviewed == date(2026, 7, 23)
    assert set(parsed.records[0]) == {"year", "title", "canonical_recall_url"}
    assert {
        record["canonical_recall_url"]
        for record in parsed.records
        if record["title"] == "Pams Frozen Berries"
    } == {
        "https://www.mpi.govt.nz/food-safety-home/food-recalls-and-complaints/"
        "recalled-food-products/pams-frozen-berries/"
    }


def test_mpi_requires_canonical_source_and_year_markers() -> None:
    missing_source = fixture_text().replace(
        "URL Source: https://www.mpi.govt.nz/food-safety-home/food-recalls-and-complaints/recalled-food-products",
        "URL Source: https://example.invalid/not-mpi",
    )
    missing_year = fixture_text().replace("## 2026 recalls\n", "## not-2026\n")
    invented_year_heading = fixture_text().replace("## 2026 recalls\n", "## 2026\n")

    with pytest.raises(MpiRecallParseError, match="canonical MPI"):
        parse_mpi_recalled_products(missing_source.encode("utf-8"), date(2026, 8, 9))
    with pytest.raises(MpiRecallParseError, match="year sections"):
        parse_mpi_recalled_products(missing_year.encode("utf-8"), date(2026, 8, 9))
    with pytest.raises(MpiRecallParseError, match="year sections"):
        parse_mpi_recalled_products(invented_year_heading.encode("utf-8"), date(2026, 8, 9))


def test_mpi_rejects_duplicate_within_year_but_keeps_three_field_allowlist() -> None:
    duplicate_link = (
        "- [Pams Frozen Berries](https://www.mpi.govt.nz/food-safety-home/"
        "food-recalls-and-complaints/recalled-food-products/pams-frozen-berries/)"
    )
    duplicate = fixture_text().replace(
        "\n## 2023 recalls\n",
        f"\n{duplicate_link}\n\n## 2023 recalls\n",
        1,
    )
    with pytest.raises(MpiRecallParseError, match="duplicate recall URL"):
        parse_mpi_recalled_products(duplicate.encode("utf-8"), date(2026, 8, 9))

    parsed = parse_mpi_recalled_products(fixture_text().encode("utf-8"), date(2026, 8, 9))
    assert all(
        set(record) == {"year", "title", "canonical_recall_url"} for record in parsed.records
    )
    assert all("Footer" not in str(record["title"]) for record in parsed.records)


def test_mpi_requires_present_valid_and_consistent_review_dates() -> None:
    missing = fixture_text().replace("Last reviewed: 23.07.26\n", "", 2)
    invalid = fixture_text().replace("Last reviewed: 23.07.26", "Last reviewed: 31.02.26", 1)
    conflicting = fixture_text().replace(
        "Last reviewed: 23.07.26\nLast reviewed: 23.07.26",
        "Last reviewed: 23.07.26\nLast reviewed: 24.07.26",
    )

    with pytest.raises(MpiRecallParseError, match="missing MPI reviewed-date"):
        parse_mpi_recalled_products(missing.encode("utf-8"), date(2026, 8, 9))
    with pytest.raises(MpiRecallParseError, match="invalid MPI reviewed-date"):
        parse_mpi_recalled_products(invalid.encode("utf-8"), date(2026, 8, 9))
    with pytest.raises(MpiRecallParseError, match="conflicting MPI reviewed-date"):
        parse_mpi_recalled_products(conflicting.encode("utf-8"), date(2026, 8, 9))


@pytest.mark.parametrize(
    "marker",
    ["Incapsula", "_Incapsula_Resource", "Request unsuccessful", "robots noindex,nofollow"],
)
def test_mpi_rejects_waf_challenge_markers_even_when_body_is_text(marker: str) -> None:
    challenged = fixture_text() + f"\n{marker}\n"
    with pytest.raises(MpiRecallParseError, match="challenge/WAF"):
        parse_mpi_recalled_products(challenged.encode("utf-8"), date(2026, 8, 9))


def test_mpi_rejects_non_canonical_links() -> None:
    invalid = fixture_text().replace(
        "https://www.mpi.govt.nz/food-safety-home/food-recalls-and-complaints/recalled-food-products/recall-2016/",
        "https://example.invalid/recall-2016/",
        1,
    )
    with pytest.raises(MpiRecallParseError, match="non-canonical recall link"):
        parse_mpi_recalled_products(invalid.encode("utf-8"), date(2026, 8, 9))
