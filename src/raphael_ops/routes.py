"""API routes for raphael-ops."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["raphael-ops"])


@router.get("")
def list_root() -> dict[str, str]:
  return {"service": "raphael-ops", "status": "stub"}
