"""Shared test fixtures for raphael-ops."""

import tempfile
from pathlib import Path

import pytest

from raphael_ops.store import OpsStore


@pytest.fixture(autouse=True)
def isolated_ops_store(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = OpsStore(db_path=Path(tmp) / "ops.db")
        from raphael_ops import routes

        monkeypatch.setattr(routes, "_store", store)
        yield
