"""Ops domain tests."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from raphael_ops.app import app


def test_health() -> None:
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["service"] == "raphael-ops"


def test_backup_creates_entry() -> None:
    client = TestClient(app)
    res = client.post("/v1/ops/backup", json={"label": "test"})
    assert res.status_code == 200
    body = res.json()
    assert body["label"] == "test"
    assert body["id"].startswith("bk-")
    assert "location" in body


@patch("raphael_ops.routes.httpx.Client")
def test_verify_integrity_reads_audit(mock_client_cls: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "valid": True,
        "events_checked": 42,
        "verified_links": 41,
        "failures": [],
    }
    mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_response

    client = TestClient(app)
    res = client.get("/v1/ops/verify-integrity")
    assert res.status_code == 200
    body = res.json()
    assert body["chain_valid"] is True
    assert body["events_checked"] == 42


def test_replay() -> None:
    with patch("raphael_ops.routes.replay_events") as mock_replay:
        mock_replay.return_value = {
            "status": "replayed",
            "events": 2,
            "replayed": ["e1", "e2"],
            "skipped": [],
            "not_found": [],
            "errors": [],
        }
        client = TestClient(app)
        res = client.post("/v1/ops/replay", json={"event_ids": ["e1", "e2"]})
        assert res.status_code == 200
        assert res.json()["events"] == 2
