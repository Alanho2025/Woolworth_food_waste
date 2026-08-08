"""P3 architecture checks: Agent orchestration and tools never import persistence."""

from __future__ import annotations

import ast
from pathlib import Path

AGENTS_ROOT = Path(__file__).resolve().parents[2] / "app" / "agents"
FORBIDDEN_ROOTS = (
    "sqlalchemy",
    "backend.app.infrastructure.db",
)


def imports_in(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def test_agent_and_tool_modules_have_no_direct_sqlalchemy_or_database_adapter_import() -> None:
    """AGENT TREE -> inspect imports -> database is reachable only via injected ports/services."""
    violations: list[str] = []
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        for imported in imports_in(path):
            if any(
                imported == forbidden or imported.startswith(f"{forbidden}.")
                for forbidden in FORBIDDEN_ROOTS
            ):
                violations.append(f"{path.relative_to(AGENTS_ROOT)} imports {imported}")

    assert violations == []
