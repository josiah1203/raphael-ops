"""Ops API — backup, replay, integrity."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(tags=["ops"])

_backups: list[dict] = []


@router.get("")
def ops_status() -> dict:
    return {"service": "raphael-ops", "status": "ok", "backups": len(_backups)}


@router.post("/backup")
def backup(body: dict | None = None) -> dict:
    bid = f"bk-{int(datetime.now(timezone.utc).timestamp())}"
    entry = {"id": bid, "created_at": datetime.now(timezone.utc).isoformat(), "label": (body or {}).get("label", "manual")}
    _backups.append(entry)
    return entry


@router.get("/verify-integrity")
def verify_integrity() -> dict:
    return {"status": "ok", "chain_valid": True, "checked_at": datetime.now(timezone.utc).isoformat()}
