"""Raphael service: raphael-ops."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from raphael_contracts.errors import ErrorResponse
from raphael_ops.routes import router

app = FastAPI(
    title="raphael-ops",
    description="Observability, reliability, release operations",
    version="0.1.0",
    openapi_url="/v1/ops/openapi.json" if "/v1/ops" else "/openapi.json",
)

app.include_router(router, prefix="/v1/ops" if "/v1/ops" else "")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "raphael-ops"}


@app.exception_handler(Exception)
async def unhandled(_request, exc: Exception) -> JSONResponse:
    err = ErrorResponse(code="internal_error", message=str(exc))
    return JSONResponse(status_code=500, content=err.model_dump())
