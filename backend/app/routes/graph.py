"""Graph routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.models import (
    SubstituteCandidate,
    SubstituteRequest,
    SubstituteResponse,
    SubstituteResult,
)

router = APIRouter(prefix="/graph", tags=["graph"])
_chaos_mode = False


@router.post("/seed")
async def seed_demo_data(request: Request) -> dict[str, str | int]:
    request_id = str(getattr(request.state, "request_id", "unknown"))
    return {
        "request_id": request_id,
        "status": "seeded",
        "nodes_created": 3,
        "edges_created": 2,
    }


@router.post("/substitutes", response_model=SubstituteResponse)
async def substitutes(
    payload: SubstituteRequest, request: Request
) -> SubstituteResponse:
    request_id = payload.request_id or str(getattr(request.state, "request_id", "unknown"))
    results: list[SubstituteResult] = []

    for bom_item in payload.bom:
        candidate = SubstituteCandidate(
            mpn=f"DEMO-{bom_item.type.upper()}-001",
            manufacturer="Demo Components",
            value=bom_item.value,
            package=bom_item.package or "unknown",
            score=80,
            reason="placeholder substitute candidate",
        )
        results.append(SubstituteResult(original=bom_item, candidates=[candidate]))

    return SubstituteResponse(request_id=request_id, results=results)


@router.post("/chaos/toggle")
async def toggle_chaos(request: Request) -> dict[str, str | bool]:
    global _chaos_mode
    _chaos_mode = not _chaos_mode

    request_id = str(getattr(request.state, "request_id", "unknown"))
    return {
        "request_id": request_id,
        "chaos_mode": _chaos_mode,
    )
