"""Architecture rules, enforced by AST analysis.

foodflow_clean_code_spec.md 2.2 points the dependency arrow inward: the domain
layer depends on nothing but the standard library and Pydantic. That is the one
architectural rule that erodes silently — a single `from sqlalchemy import ...`
added to a policy module never fails a unit test, and by the time anyone
notices, the rule is gone.

Grep would be the obvious tool and the wrong one: it matches strings inside
docstrings and comments (this file's own docstring names every forbidden
package), and it misses `importlib.import_module("sqlalchemy")`. So the check
parses each module and inspects `Import` and `ImportFrom` nodes.

The checker itself is verified in `test_the_checker_detects_a_deliberately_bad_import`,
which builds a throwaway package containing a real violation. Without that, a
checker with an inverted condition would sit permanently green.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = PROJECT_ROOT / "backend" / "app"
DOMAIN_ROOT = APP_ROOT / "domain"

# foodflow_clean_code_spec.md 2.2 / backend/app/domain/ports.py docstring.
FORBIDDEN_IN_DOMAIN = frozenset(
    {
        "fastapi",
        "starlette",
        "sqlalchemy",
        "google.adk",
        "litellm",
        "openai",
    }
)

# The dependency arrow points inward: the domain never reaches back out.
FORBIDDEN_INTERNAL_IN_DOMAIN = frozenset(
    {
        "backend.app.api",
        "backend.app.agents",
        "backend.app.infrastructure",
        "backend.app.application",
        "backend.app.seed",
    }
)


# --------------------------------------------------------------------------
# AST helpers
# --------------------------------------------------------------------------


def python_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def module_name_for(path: Path) -> str:
    """Dotted module name of a file inside the repository.

    Files outside the repository (the synthetic packages the checker's own
    self-tests build under tmp_path) fall back to their basename, which is
    enough for relative-import resolution in a flat throwaway package.
    """
    try:
        relative = path.relative_to(PROJECT_ROOT).with_suffix("")
    except ValueError:
        relative = Path(path.name).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def imported_names(path: Path) -> Iterator[tuple[int, str]]:
    """Yield (line number, absolute dotted name) for every import in a module.

    Relative imports are resolved against the module's own package so that
    `from ..domain import clock` is comparable with an absolute name. Imports
    inside `if TYPE_CHECKING:` are included deliberately: a domain type
    annotated with a SQLAlchemy type still couples the domain to SQLAlchemy.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    package_parts = module_name_for(path).split(".")
    if path.name != "__init__.py":
        package_parts = package_parts[:-1]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package_parts[: len(package_parts) - (node.level - 1)]
                prefix = ".".join([*base, node.module] if node.module else base)
            else:
                prefix = node.module or ""
            for alias in node.names:
                yield node.lineno, f"{prefix}.{alias.name}" if prefix else alias.name
                yield node.lineno, prefix
        elif isinstance(node, ast.Call):
            # importlib.import_module("sqlalchemy") and __import__("sqlalchemy")
            func = node.func
            name = (
                func.attr
                if isinstance(func, ast.Attribute)
                else func.id
                if isinstance(func, ast.Name)
                else ""
            )
            if name in {"import_module", "__import__"} and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    yield node.lineno, first.value


def matches(dotted: str, forbidden: frozenset[str]) -> str | None:
    """Return the forbidden root that `dotted` belongs to, if any."""
    for banned in forbidden:
        if dotted == banned or dotted.startswith(f"{banned}."):
            return banned
    return None


def forbidden_imports(root: Path, forbidden: frozenset[str]) -> list[str]:
    """Every violation under `root`, as human-readable 'file:line imports x' lines."""
    violations: list[str] = []
    for path in python_files(root):
        for lineno, dotted in imported_names(path):
            banned = matches(dotted, forbidden)
            if banned is not None:
                relative = path.relative_to(PROJECT_ROOT)
                violations.append(f"{relative}:{lineno} imports {dotted!r} (forbidden: {banned})")
    return sorted(set(violations))


# --------------------------------------------------------------------------
# Forbidden imports
# --------------------------------------------------------------------------


def test_domain_layer_importing_a_framework_is_reported_as_a_violation() -> None:
    """DOMAIN LAYER -> scan every module -> zero framework imports.

    clean_code_spec 2.2. The domain is pure Python plus Pydantic.
    """
    assert DOMAIN_ROOT.is_dir(), f"{DOMAIN_ROOT} must exist"
    violations = forbidden_imports(DOMAIN_ROOT, FORBIDDEN_IN_DOMAIN)
    assert violations == [], "backend/app/domain must not import a framework:\n" + "\n".join(
        violations
    )


def test_domain_layer_importing_an_outer_layer_is_reported_as_a_violation() -> None:
    """DOMAIN LAYER -> scan every module -> no import of api, agents, infra, application, seed.

    The dependency arrow points inward (clean_code_spec 2.2). Infrastructure
    depends on the domain through the ports in `domain/ports.py`, never the
    reverse.
    """
    violations = forbidden_imports(DOMAIN_ROOT, FORBIDDEN_INTERNAL_IN_DOMAIN)
    assert violations == [], "backend/app/domain must not depend outward:\n" + "\n".join(violations)


def test_contracts_layer_importing_a_framework_is_reported_as_a_violation() -> None:
    """CONTRACTS LAYER -> scan every module -> zero framework imports.

    The typed contracts are the integration seam shared by persistence, tools,
    the API, and the generated frontend client (contracts/core.py docstring). A
    SQLAlchemy import here would make a persistence model reachable as an API
    schema, which clean_code_spec 4 and 9 forbid.
    """
    contracts_root = APP_ROOT / "contracts"
    assert contracts_root.is_dir(), f"{contracts_root} must exist"
    violations = forbidden_imports(contracts_root, FORBIDDEN_IN_DOMAIN)
    assert violations == [], "backend/app/contracts must not import a framework:\n" + "\n".join(
        violations
    )


def test_the_checker_detects_a_deliberately_bad_import(tmp_path: Path) -> None:
    """CHECKER -> run over a package containing `import sqlalchemy` -> reports it.

    Proves the check is capable of failing. A permanently-green architecture
    test is worse than none, because it is trusted.
    """
    package = tmp_path / "fakedomain"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "policy.py").write_text(
        "import sqlalchemy\nfrom fastapi import APIRouter\n", encoding="utf-8"
    )

    found = [
        line
        for path in python_files(package)
        for lineno, dotted in imported_names(path)
        if matches(dotted, FORBIDDEN_IN_DOMAIN)
        for line in [f"{path.name}:{lineno} {dotted}"]
    ]
    assert any("sqlalchemy" in line for line in found), found
    assert any("fastapi" in line for line in found), found


def test_the_checker_detects_a_dynamic_import_that_grep_would_miss(tmp_path: Path) -> None:
    """CHECKER -> run over `importlib.import_module("litellm")` -> reports it."""
    module = tmp_path / "sneaky.py"
    module.write_text(
        'import importlib\nengine = importlib.import_module("litellm")\n', encoding="utf-8"
    )
    found = [dotted for _, dotted in imported_names(module) if matches(dotted, FORBIDDEN_IN_DOMAIN)]
    assert "litellm" in found, found


def test_the_checker_ignores_a_forbidden_name_that_only_appears_in_a_comment(
    tmp_path: Path,
) -> None:
    """CHECKER -> run over a module mentioning 'sqlalchemy' in prose -> reports nothing.

    This is why the check is AST-based and not grep-based: this very file's
    docstring names every forbidden package.
    """
    module = tmp_path / "prose.py"
    module.write_text(
        '"""This module deliberately does not import sqlalchemy or fastapi."""\n'
        "# fastapi is not used here\n"
        'NOTE = "openai"\n',
        encoding="utf-8",
    )
    found = [dotted for _, dotted in imported_names(module) if matches(dotted, FORBIDDEN_IN_DOMAIN)]
    assert found == [], found


# --------------------------------------------------------------------------
# Import cycles
# --------------------------------------------------------------------------


def internal_import_graph(root: Path) -> dict[str, set[str]]:
    """Module -> set of first-party modules it imports.

    Only edges between modules that actually exist in the tree are kept, and a
    `from backend.app.domain import clock` edge is normalised onto the module
    `backend.app.domain.clock` when that module exists, so package-level and
    module-level imports produce the same graph.
    """
    modules = {module_name_for(p): p for p in python_files(root)}
    graph: dict[str, set[str]] = {name: set() for name in modules}
    for name, path in modules.items():
        for _lineno, dotted in imported_names(path):
            if not dotted.startswith("backend."):
                continue
            target = dotted
            while target and target not in modules:
                target, _, _ = target.rpartition(".")
            if target and target != name:
                graph[name].add(target)
    return graph


def find_cycle(graph: dict[str, set[str]]) -> list[str] | None:
    """Return one cycle as a path, or None. Iterative DFS with a colour marking."""
    white, grey, black = 0, 1, 2
    colour = dict.fromkeys(graph, white)
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        colour[node] = grey
        stack.append(node)
        for neighbour in sorted(graph[node]):
            if colour.get(neighbour, black) == grey:
                return [*stack[stack.index(neighbour) :], neighbour]
            if colour.get(neighbour, black) == white:
                found = visit(neighbour)
                if found is not None:
                    return found
        stack.pop()
        colour[node] = black
        return None

    for node in sorted(graph):
        if colour[node] == white:
            found = visit(node)
            if found is not None:
                return found
    return None


def test_backend_app_module_graph_contains_no_import_cycle() -> None:
    """BACKEND APP -> build the first-party import graph -> no cycle exists.

    A cycle in Python is not always an ImportError; it often surfaces as a
    half-initialised module under one import order and works under another,
    which is the shape of a bug that appears for the first time in CI.
    """
    cycle = find_cycle(internal_import_graph(APP_ROOT))
    assert cycle is None, "import cycle: " + " -> ".join(cycle or [])


def test_the_cycle_detector_reports_a_deliberately_circular_graph() -> None:
    """DETECTOR -> run over a -> b -> a -> reports the cycle.

    Same reasoning as the bad-import proof: an assertion that cannot fail is
    not an assertion.
    """
    cycle = find_cycle({"a": {"b"}, "b": {"a"}})
    assert cycle is not None
    assert cycle[0] == cycle[-1], cycle


# --------------------------------------------------------------------------
# The wall clock
# --------------------------------------------------------------------------


def test_no_module_outside_domain_clock_reads_the_wall_clock_directly() -> None:
    """BACKEND APP -> scan for datetime.now / datetime.utcnow / time.time -> only clock.py.

    docs/assumption_audit.md C-1: if the demo runs at 10:00, every community is
    legitimately closed and the pitch dies through no fault of the logic. "Now"
    is injected through the `Clock` port. One direct `datetime.now()` anywhere
    in a receiving-window path silently reintroduces the failure, and it is
    invisible in every test that happens to run inside the window.
    """
    allowed = {APP_ROOT / "domain" / "clock.py"}
    offenders: list[str] = []
    for path in python_files(APP_ROOT):
        if path in allowed:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            attribute = node.func.attr
            value = node.func.value
            owner = value.id if isinstance(value, ast.Name) else ""
            if attribute in {"now", "utcnow"} and owner in {"datetime", "date"}:
                offenders.append(
                    f"{path.relative_to(PROJECT_ROOT)}:{node.lineno} {owner}.{attribute}()"
                )
            if attribute == "time" and owner == "time":
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{node.lineno} time.time()")
    assert offenders == [], (
        "read the wall clock outside domain/clock.py; inject the Clock port instead:\n"
        + "\n".join(offenders)
    )


@pytest.mark.parametrize("layer", ["domain", "contracts"])
def test_named_layer_directory_exists(layer: str) -> None:
    """REPOSITORY -> look for the layer directory -> it is present.

    Guards the checks above against silently passing over an empty tree, which
    is how an architecture test survives a refactor that deleted its subject.
    """
    root = APP_ROOT / layer
    assert root.is_dir(), f"{root} is missing"
    assert python_files(root), f"{root} contains no Python modules"
