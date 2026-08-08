#!/usr/bin/env python3
"""Reject breaking changes against the P2 frozen OpenAPI artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.generate_openapi import DEFAULT_OUTPUT, build_openapi  # noqa: E402

HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete"})


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"OpenAPI document must be an object: {path}")
    return value


def _schema_compat(
    frozen: object,
    candidate: object,
    location: str,
    violations: list[str],
) -> None:
    if not isinstance(frozen, dict):
        if frozen != candidate:
            violations.append(f"{location}: changed from {frozen!r} to {candidate!r}")
        return
    if not isinstance(candidate, dict):
        violations.append(f"{location}: schema object was removed")
        return

    for keyword in ("$ref", "type", "format", "const", "discriminator"):
        if keyword in frozen and candidate.get(keyword) != frozen[keyword]:
            violations.append(f"{location}: changed {keyword}")

    frozen_enum = frozen.get("enum")
    if isinstance(frozen_enum, list):
        candidate_enum = candidate.get("enum")
        if not isinstance(candidate_enum, list) or not set(frozen_enum).issubset(candidate_enum):
            violations.append(f"{location}: removed an accepted enum value")

    frozen_required = frozen.get("required", [])
    candidate_required = candidate.get("required", [])
    if frozen_required != candidate_required:
        violations.append(f"{location}: changed required fields")

    frozen_properties = frozen.get("properties", {})
    candidate_properties = candidate.get("properties", {})
    if isinstance(frozen_properties, dict):
        if not isinstance(candidate_properties, dict):
            violations.append(f"{location}: removed object properties")
        else:
            for name, old_property in frozen_properties.items():
                if name not in candidate_properties:
                    violations.append(f"{location}: removed property {name}")
                else:
                    _schema_compat(
                        old_property,
                        candidate_properties[name],
                        f"{location}.properties.{name}",
                        violations,
                    )

    for keyword in ("items", "additionalProperties"):
        if keyword in frozen:
            _schema_compat(
                frozen[keyword],
                candidate.get(keyword),
                f"{location}.{keyword}",
                violations,
            )

    for keyword in ("anyOf", "oneOf", "allOf"):
        old_variants = frozen.get(keyword)
        if not isinstance(old_variants, list):
            continue
        new_variants = candidate.get(keyword)
        if not isinstance(new_variants, list) or len(new_variants) != len(old_variants):
            violations.append(f"{location}: changed {keyword} variants")
            continue
        for index, old_variant in enumerate(old_variants):
            _schema_compat(
                old_variant,
                new_variants[index],
                f"{location}.{keyword}[{index}]",
                violations,
            )


def compatibility_violations(frozen: dict[str, Any], candidate: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    frozen_paths = frozen.get("paths", {})
    candidate_paths = candidate.get("paths", {})
    if not isinstance(frozen_paths, dict) or not isinstance(candidate_paths, dict):
        return ["paths: missing paths object"]

    for path, old_path_item in frozen_paths.items():
        new_path_item = candidate_paths.get(path)
        if not isinstance(old_path_item, dict) or not isinstance(new_path_item, dict):
            violations.append(f"paths.{path}: path was removed")
            continue
        for method in HTTP_METHODS.intersection(old_path_item):
            if method not in new_path_item:
                violations.append(f"paths.{path}.{method}: operation was removed")
                continue
            old_operation = old_path_item[method]
            new_operation = new_path_item[method]
            if not isinstance(old_operation, dict) or not isinstance(new_operation, dict):
                violations.append(f"paths.{path}.{method}: operation shape changed")
                continue
            _operation_compat(
                old_operation,
                new_operation,
                f"paths.{path}.{method}",
                violations,
            )

    frozen_schemas = frozen.get("components", {}).get("schemas", {})
    candidate_schemas = candidate.get("components", {}).get("schemas", {})
    if not isinstance(frozen_schemas, dict) or not isinstance(candidate_schemas, dict):
        violations.append("components.schemas: missing schema registry")
        return violations
    for name, old_schema in frozen_schemas.items():
        if name not in candidate_schemas:
            violations.append(f"components.schemas.{name}: schema was removed")
        else:
            _schema_compat(
                old_schema,
                candidate_schemas[name],
                f"components.schemas.{name}",
                violations,
            )
    return violations


def _operation_compat(
    frozen: dict[str, Any],
    candidate: dict[str, Any],
    location: str,
    violations: list[str],
) -> None:
    old_parameters = frozen.get("parameters", [])
    new_parameters = candidate.get("parameters", [])
    if isinstance(old_parameters, list):
        if not isinstance(new_parameters, list):
            violations.append(f"{location}: parameters were removed")
        else:
            new_by_key = {
                (item.get("name"), item.get("in")): item
                for item in new_parameters
                if isinstance(item, dict)
            }
            for parameter in old_parameters:
                if not isinstance(parameter, dict):
                    continue
                key = (parameter.get("name"), parameter.get("in"))
                replacement = new_by_key.get(key)
                if replacement is None:
                    violations.append(f"{location}: removed parameter {key}")
                    continue
                if parameter.get("required") != replacement.get("required"):
                    violations.append(f"{location}: changed required flag for parameter {key}")
                _schema_compat(
                    parameter.get("schema", {}),
                    replacement.get("schema", {}),
                    f"{location}.parameters.{key}",
                    violations,
                )

    old_body = frozen.get("requestBody")
    new_body = candidate.get("requestBody")
    if isinstance(old_body, dict):
        if not isinstance(new_body, dict):
            violations.append(f"{location}: request body was removed")
        else:
            if old_body.get("required") != new_body.get("required"):
                violations.append(f"{location}: changed request-body required flag")
            _content_compat(old_body, new_body, f"{location}.requestBody", violations)

    old_responses = frozen.get("responses", {})
    new_responses = candidate.get("responses", {})
    if isinstance(old_responses, dict):
        if not isinstance(new_responses, dict):
            violations.append(f"{location}: responses were removed")
        else:
            for code, old_response in old_responses.items():
                new_response = new_responses.get(code)
                if not isinstance(old_response, dict) or not isinstance(new_response, dict):
                    violations.append(f"{location}: removed response {code}")
                    continue
                _content_compat(
                    old_response,
                    new_response,
                    f"{location}.responses.{code}",
                    violations,
                )


def _content_compat(
    frozen: dict[str, Any],
    candidate: dict[str, Any],
    location: str,
    violations: list[str],
) -> None:
    old_content = frozen.get("content", {})
    new_content = candidate.get("content", {})
    if not isinstance(old_content, dict):
        return
    if not isinstance(new_content, dict):
        violations.append(f"{location}: content was removed")
        return
    for media_type, old_media in old_content.items():
        new_media = new_content.get(media_type)
        if not isinstance(old_media, dict) or not isinstance(new_media, dict):
            violations.append(f"{location}: removed media type {media_type}")
            continue
        _schema_compat(
            old_media.get("schema", {}),
            new_media.get("schema", {}),
            f"{location}.content.{media_type}.schema",
            violations,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--candidate",
        type=Path,
        help="Candidate OpenAPI JSON; defaults to the contract-only exporter.",
    )
    args = parser.parse_args()
    frozen = _read(args.frozen)
    candidate = _read(args.candidate) if args.candidate else build_openapi()
    violations = compatibility_violations(frozen, candidate)
    if violations:
        print("Breaking OpenAPI changes detected:")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("OpenAPI candidate is backward-compatible with the P2 freeze")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
