"""Explicit opt-in for the committed P0 live spike.

The phase plan's reproducibility command is intentionally exact::

    pytest backend/tests/spike -v --no-skip

`--no-skip` only affects tests under this spike directory. It also clears the
repository-wide marker expression which normally deselects `spike` and `live`.
The test itself still calls `Settings.require_deepseek_key()`, so opting in
without a key fails before any provider request is attempted.
"""

from __future__ import annotations

from pathlib import Path

import pytest

SPIKE_ROOT = Path(__file__).parent.resolve()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--no-skip",
        action="store_true",
        default=False,
        help="Run the P0 live spike which is skipped and deselected by default.",
    )


def pytest_configure(config: pytest.Config) -> None:
    if config.getoption("--no-skip"):
        config.option.markexpr = ""


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if not config.getoption("--no-skip"):
        return
    for item in items:
        item_path = Path(str(item.path)).resolve()
        if item_path.is_relative_to(SPIKE_ROOT):
            item.own_markers[:] = [marker for marker in item.own_markers if marker.name != "skip"]
