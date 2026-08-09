import copy
import json
from pathlib import Path

import pytest

from backend.app.etl.sources.woolworths import (
    WoolworthsParseError,
    parse_woolworths_store_locator,
)

FIXTURE = Path(__file__).parent / "fixtures/woolworths-minimal.json"


def fixture_payload() -> bytes:
    return FIXTURE.read_bytes()


def test_woolworths_filters_nested_store_details_and_emits_strict_allowlist() -> None:
    parsed = parse_woolworths_store_locator(fixture_payload(), expected_count=2)

    assert parsed.before_count == 5
    assert parsed.auk_count == 4
    assert parsed.division_count == 2
    assert parsed.filter_counts == {
        "input_records": 5,
        "state_AUK": 4,
        "division_COUNTDOWN": 2,
    }
    assert [record["storeNumber"] for record in parsed.records] == ["3", "20"]
    assert parsed.records[0]["postcode"] == "0204"
    assert parsed.records[1]["postcode"] == "0618"
    assert parsed.records[1]["addressLine2"] is None
    assert parsed.drift == ()
    assert set(parsed.records[0]) == {
        "storeNumber",
        "name",
        "addressLine1",
        "addressLine2",
        "suburb",
        "postcode",
        "state",
        "country",
        "latitude",
        "longitude",
        "division",
    }
    assert all(
        forbidden not in record
        for record in parsed.records
        for forbidden in ("manager", "email", "phone", "facilities", "tradingHours")
    )


def test_woolworths_output_is_stable_under_irrelevant_input_reordering() -> None:
    document = json.loads(fixture_payload())
    reordered = copy.deepcopy(document)
    reordered["Locator"]["storelist"] = list(reversed(reordered["Locator"]["storelist"]))
    reordered["Locator"]["storelist"][0]["storeDetail"]["facilityList"] = ["z", "a"]

    first = parse_woolworths_store_locator(fixture_payload()).records
    second = parse_woolworths_store_locator(
        json.dumps(reordered, ensure_ascii=False).encode("utf-8")
    ).records

    assert first == second


def test_woolworths_rejects_duplicate_store_number() -> None:
    document = json.loads(fixture_payload())
    document["Locator"]["storelist"].append(copy.deepcopy(document["Locator"]["storelist"][0]))

    with pytest.raises(WoolworthsParseError, match="duplicate store number"):
        parse_woolworths_store_locator(json.dumps(document).encode("utf-8"))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("no", None, "no"),
        ("latitude", "not-a-coordinate", "latitude"),
        ("longtitude", 181, "longtitude"),
        ("postcode", "10000", "postcode"),
    ],
)
def test_woolworths_rejects_missing_or_invalid_identity_coordinates_and_postcode(
    field: str, value: object, message: str
) -> None:
    document = json.loads(fixture_payload())
    detail = document["Locator"]["storelist"][0]["storeDetail"]
    detail[field] = value

    with pytest.raises(WoolworthsParseError, match=message):
        parse_woolworths_store_locator(json.dumps(document).encode("utf-8"))


def test_woolworths_rejects_normalized_store_number_as_source_key() -> None:
    document = json.loads(fixture_payload())
    detail = document["Locator"]["storelist"][0]["storeDetail"]
    detail["storeNumber"] = detail.pop("no")

    with pytest.raises(WoolworthsParseError, match=r"selected store 0\.no"):
        parse_woolworths_store_locator(json.dumps(document).encode("utf-8"))


def test_woolworths_requires_locator_storelist_store_shape() -> None:
    with pytest.raises(WoolworthsParseError, match="storelist"):
        parse_woolworths_store_locator(b'{"Locator": {"stores": []}}')
    with pytest.raises(WoolworthsParseError, match="storeDetail"):
        parse_woolworths_store_locator(b'{"Locator": {"storelist": [{"tradingHours": {}}]}}')
