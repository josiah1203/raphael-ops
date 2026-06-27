"""Replay events via the audit API with idempotent tracking."""

from __future__ import annotations

import os
from typing import Any

import httpx

from raphael_ops.store import OpsStore


def audit_url() -> str:
    return os.environ.get("RAPHAEL_AUDIT_URL", "http://127.0.0.1:8093").rstrip("/")


def replay_events(event_ids: list[str], store: OpsStore | None = None) -> dict[str, Any]:
    store = store or OpsStore()
    replayed: list[str] = []
    skipped: list[str] = []
    not_found: list[str] = []
    errors: list[dict[str, str]] = []

    with httpx.Client(timeout=15.0) as client:
        for event_id in event_ids:
            if store.was_replayed(event_id):
                skipped.append(event_id)
                continue
            try:
                res = client.get(f"{audit_url()}/v1/audit/events/{event_id}")
            except httpx.HTTPError as exc:
                errors.append({"event_id": event_id, "error": str(exc)})
                continue
            if res.status_code != 200:
                not_found.append(event_id)
                continue
            body = res.json()
            event = body.get("event") or {}
            if event.get("status") == "not_found" or not event.get("event_id"):
                not_found.append(event_id)
                continue
            try:
                from raphael_contracts.kafka import publish_event

                publish_event(
                    f"raphael.audit.replay.{event.get('event_type', 'event').replace('.', '_')}",
                    {
                        "event_id": event.get("event_id"),
                        "event_type": event.get("event_type"),
                        "payload": event.get("payload"),
                        "session_id": event.get("session_id"),
                        "project_id": event.get("project_id"),
                    },
                    source="raphael-ops",
                    workspace_id=event.get("project_id"),
                )
            except Exception as exc:
                errors.append({"event_id": event_id, "error": str(exc)})
                continue
            store.mark_replayed(event_id)
            replayed.append(event_id)

    return {
        "status": "replayed" if replayed else ("skipped" if skipped and not errors else "partial"),
        "events": len(replayed),
        "replayed": replayed,
        "skipped": skipped,
        "not_found": not_found,
        "errors": errors,
    }
