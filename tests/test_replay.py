"""Replay domain tests."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from raphael_ops.app import app
from raphael_ops.replay import replay_events
from raphael_ops.store import OpsStore


def test_replay_fetches_from_audit_and_tracks_idempotency() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = OpsStore(db_path=Path(tmp) / "ops.db")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "event": {
                "event_id": "ev-replay-1",
                "event_type": "design.save",
                "payload": {"document_id": "doc-1"},
                "session_id": "sess-1",
                "project_id": "proj-1",
            }
        }

        with patch("raphael_ops.replay.httpx.Client") as mock_client_cls, patch(
            "raphael_contracts.kafka.publish_event"
        ) as mock_publish:
            mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_response

            result = replay_events(["ev-replay-1"], store)
            assert result["events"] == 1
            assert "ev-replay-1" in result["replayed"]
            mock_publish.assert_called_once()

            second = replay_events(["ev-replay-1"], store)
            assert second["events"] == 0
            assert "ev-replay-1" in second["skipped"]


def test_replay_route() -> None:
    with patch("raphael_ops.routes.replay_events") as mock_replay:
        mock_replay.return_value = {
            "status": "replayed",
            "events": 1,
            "replayed": ["ev-1"],
            "skipped": [],
            "not_found": [],
            "errors": [],
        }
        client = TestClient(app)
        res = client.post("/v1/ops/replay", json={"event_ids": ["ev-1"]})
        assert res.status_code == 200
        body = res.json()
        assert body["events"] == 1
        assert "replayed_at" in body
        mock_replay.assert_called_once()
