"""Pure parser for the Woolworths NZ Store Locator response."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


class WoolworthsParseError(ValueError):
    """Raised when the reviewed Woolworths response contract is not met."""


@dataclass(frozen=True, slots=True)
class WoolworthsParseResult:
    """Deterministic allowlisted records and source filter metadata."""

    records: tuple[dict[str, object], ...]
    before_count: int
    auk_count: int
    division_count: int
    warnings: tuple[str, ...]
    drift: tuple[str, ...]

    @property
    def filter_counts(self) -> dict[str, int]:
        return {
            "input_records": self.before_count,
            "state_AUK": self.auk_count,
            "division_COUNTDOWN": self.division_count,
        }


def _mapping(value: object, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise WoolworthsParseError(f"{context} must be an object")
    return value


def _required_string(detail: Mapping[str, Any], key: str, context: str) -> str:
    value = detail.get(key)
    if not isinstance(value, str) or not value.strip() or value.strip() == "null":
        raise WoolworthsParseError(f"{context}.{key} must be a non-empty string")
    return value.strip()


def _required_name(detail: Mapping[str, Any], context: str) -> str:
    for key in ("name", "storeName"):
        if key in detail:
            return _required_string(detail, key, context)
    raise WoolworthsParseError(f"{context}.name is required")


def _normalise_nullable_string(value: object, context: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise WoolworthsParseError(f"{context} must be a string or null")
    text = value.strip()
    return None if not text or text == "null" else text


def _postcode(value: object, context: str) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise WoolworthsParseError(f"{context} must be a numeric string")
    text = str(value).strip()
    if not text.isdigit():
        raise WoolworthsParseError(f"{context} must be a numeric string")
    numeric = int(text)
    if numeric < 0 or numeric > 9999:
        raise WoolworthsParseError(f"{context} must fit a four-digit postcode")
    return f"{numeric:04d}"


def _coordinate(value: object, key: str, context: str, lower: float, upper: float) -> float:
    if value == "null" or value is None or isinstance(value, bool):
        raise WoolworthsParseError(f"{context}.{key} is required")
    if not isinstance(value, (int, float, str)):
        raise WoolworthsParseError(f"{context}.{key} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise WoolworthsParseError(f"{context}.{key} must be numeric") from exc
    if not math.isfinite(number) or not lower <= number <= upper:
        raise WoolworthsParseError(f"{context}.{key} is outside its valid range")
    return number


def _store_number(value: object, context: str) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise WoolworthsParseError(f"{context}.no must be a numeric string")
    text = str(value).strip()
    if not text.isdigit():
        raise WoolworthsParseError(f"{context}.no must be a numeric string")
    return text


def parse_woolworths_store_locator(
    payload: bytes, expected_count: int | None = None
) -> WoolworthsParseResult:
    """Parse exact response bytes into sorted, allowlisted supermarket records."""

    try:
        document = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WoolworthsParseError("response is not valid UTF-8 JSON") from exc

    root = _mapping(document, "response")
    locator = _mapping(root.get("Locator"), "response.Locator")
    storelist_value = locator.get("storelist")
    if not isinstance(storelist_value, list):
        raise WoolworthsParseError("response.Locator.storelist must be a list")

    auk_details: list[Mapping[str, Any]] = []
    countdown_details: list[Mapping[str, Any]] = []
    for index, item in enumerate(storelist_value):
        item_object = _mapping(item, f"response.Locator.storelist[{index}]")
        detail = _mapping(
            item_object.get("storeDetail"),
            f"response.Locator.storelist[{index}].storeDetail",
        )
        if detail.get("state") == "AUK":
            auk_details.append(detail)
            if detail.get("division") == "COUNTDOWN":
                countdown_details.append(detail)

    records: list[dict[str, object]] = []
    seen_store_numbers: set[str] = set()
    for index, detail in enumerate(countdown_details):
        context = f"selected store {index}"
        # The source calls this identity field `no`; `storeNumber` is the
        # normalized Phase 1 output name only.
        store_number = _store_number(detail.get("no"), context)
        if store_number in seen_store_numbers:
            raise WoolworthsParseError(f"duplicate store number: {store_number}")
        seen_store_numbers.add(store_number)
        record: dict[str, object] = {
            "storeNumber": store_number,
            "name": _required_name(detail, context),
            "addressLine1": _required_string(detail, "addressLine1", context),
            "addressLine2": _normalise_nullable_string(
                detail.get("addressLine2"), f"{context}.addressLine2"
            ),
            "suburb": _required_string(detail, "suburb", context),
            "postcode": _postcode(detail.get("postcode"), f"{context}.postcode"),
            "state": _required_string(detail, "state", context),
            "country": _required_string(detail, "country", context),
            "latitude": _coordinate(detail.get("latitude"), "latitude", context, -90.0, 90.0),
            "longitude": _coordinate(
                detail.get("longtitude"), "longtitude", context, -180.0, 180.0
            ),
            "division": _required_string(detail, "division", context),
        }
        records.append(record)

    records.sort(key=lambda record: (int(str(record["storeNumber"])), str(record["storeNumber"])))
    drift: tuple[str, ...] = ()
    if expected_count is not None and len(records) != expected_count:
        drift = (f"expected {expected_count} COUNTDOWN/AUK records, observed {len(records)}",)
    return WoolworthsParseResult(
        records=tuple(records),
        before_count=len(storelist_value),
        auk_count=len(auk_details),
        division_count=len(countdown_details),
        warnings=(),
        drift=drift,
    )
