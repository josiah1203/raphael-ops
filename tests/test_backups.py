"""Backup domain tests."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from raphael_ops.app import app


def test_backup_persists_to_store_not_memory_list() -> None:
    from raphael_ops import routes

    with patch("raphael_ops.routes.put_backup", return_value="file:///tmp/bk-test.json"):
        client = TestClient(app)
        res = client.post("/v1/ops/backup", json={"label": "nightly"})
        assert res.status_code == 200
        body = res.json()
        assert body["label"] == "nightly"
        assert body["id"].startswith("bk-")
        assert body["location"] == "file:///tmp/bk-test.json"

    assert routes._store.backup_count() == 1
    backups = routes._store.list_backups()
    assert len(backups) == 1
    assert backups[0]["label"] == "nightly"


def test_list_backups_route() -> None:
    from raphael_ops import routes

    routes._store.add_backup(
        {
            "id": "bk-test",
            "label": "manual",
            "location": "s3://raphael-backups/bk-test.json",
            "created_at": "2026-01-01T00:00:00+00:00",
            "services": ["audit"],
        }
    )

    client = TestClient(app)
    res = client.get("/v1/ops/backups")
    assert res.status_code == 200
    assert len(res.json()["backups"]) == 1
    assert res.json()["backups"][0]["id"] == "bk-test"
