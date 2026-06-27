"""Ops API — backup, replay, integrity."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter

from raphael_ops.blob import put_backup
from raphael_ops.replay import audit_url, replay_events
from raphael_ops.store import OpsStore

router = APIRouter(tags=["ops"])

_store = OpsStore()


@router.get("")
def ops_status() -> dict[str, Any]:
    return {"service": "raphael-ops", "status": "ok", "backups": _store.backup_count()}


@router.get("/backups")
def list_backups() -> dict[str, Any]:
    return {"backups": _store.list_backups()}


@router.post("/backup")
def backup(body: dict[str, Any] | None = None) -> dict[str, Any]:
    bid = f"bk-{int(datetime.now(timezone.utc).timestamp())}"
    label = (body or {}).get("label", "manual")
    snapshot = {
        "id": bid,
        "label": label,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "services": ["audit", "workspaces", "orgs"],
    }
    location = put_backup(f"backups/{bid}.json", snapshot)
    entry = {**snapshot, "location": location}
    _store.add_backup(entry)
    return entry


@router.get("/verify-integrity")
def verify_integrity() -> dict[str, Any]:
    checked_at = datetime.now(timezone.utc).isoformat()
    try:
        with httpx.Client(timeout=10.0) as client:
            res = client.get(f"{audit_url()}/v1/audit/verify")
            if res.status_code == 200:
                audit = res.json()
                return {
                    "status": "ok" if audit.get("valid", True) else "failed",
                    "chain_valid": audit.get("valid", True),
                    "events_checked": audit.get("events_checked", 0),
                    "verified_links": audit.get("verified_links", 0),
                    "failures": audit.get("failures", []),
                    "checked_at": checked_at,
                }
    except httpx.HTTPError as exc:
        return {"status": "error", "chain_valid": False, "error": str(exc), "checked_at": checked_at}
    return {"status": "unknown", "chain_valid": False, "checked_at": checked_at}


@router.post("/replay")
def replay(body: dict[str, Any] | None = None) -> dict[str, Any]:
    event_ids = (body or {}).get("event_ids", (body or {}).get("events", []))
    result = replay_events(event_ids, _store)
    result["replayed_at"] = datetime.now(timezone.utc).isoformat()
    return result
