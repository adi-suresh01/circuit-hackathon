"""Graph routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from app.config import settings
from app.models import (
    SubstituteRequest,
    SubstituteResponse,
    SubstituteResult,
)
from app.services.neo4j_graph import Neo4jGraph
from app.state import runtime_state

router = APIRouter(prefix="/graph", tags=["graph"])
logger = logging.getLogger(__name__)
graph_service = Neo4jGraph(
    uri=settings.neo4j_uri,
    username=settings.neo4j_username,
    password=settings.neo4j_password,
)


def close_graph_service() -> None:
    graph_service.close()


@router.post("/seed")
async def seed_demo_data(request: Request) -> dict[str, str | int]:
    request_id = str(getattr(request.state, "request_id", "unknown"))
    try:
        seed_stats = graph_service.seed_demo_data()
    except Exception as exc:
        logger.exception("Neo4j seed failed", exc_info=exc)
        raise HTTPException(
            status_code=503,
            detail="Unable to seed graph data. Verify Neo4j connectivity.",
        ) from exc

    return {
        "request_id": request_id,
        "status": "seeded",
        "parts_seeded": int(seed_stats["parts_seeded"]),
        "relationships_seeded": int(seed_stats["relationships_seeded"]),
        "parts_total": int(seed_stats["parts_total"]),
        "relationships_total": int(seed_stats["relationships_total"]),
    }


@router.post("/substitutes", response_model=SubstituteResponse)
async def substitutes(
    payload: SubstituteRequest, request: Request
) -> SubstituteResponse:
    request_id = payload.request_id or str(getattr(request.state, "request_id", "unknown"))
    chaos_active = runtime_state.is_chaos_mode()
    constraints = payload.constraints or {}
    raw_limit = constraints.get("limit", 5)
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        limit = 5
    limit = max(1, min(limit, 20))

    results: list[SubstituteResult] = []

    try:
        for bom_item in payload.bom:
            candidates = graph_service.find_substitutes(bom_item, limit=limit)
            results.append(SubstituteResult(original=bom_item, candidates=candidates))
    except Exception as exc:
        logger.exception("Neo4j substitute lookup failed", exc_info=exc)
        raise HTTPException(
            status_code=503,
            detail="Unable to query substitutes. Verify Neo4j connectivity.",
        ) from exc

    warnings: list[str] = []
    if chaos_active:
        warnings.append(
            "Chaos mode active: added artificial 1.5s substitute query delay."
        )

    return SubstituteResponse(request_id=request_id, results=results, warnings=warnings)


@router.post("/chaos/toggle")
async def toggle_chaos(request: Request) -> dict[str, str | bool]:
    chaos_mode = runtime_state.toggle_chaos_mode()
    request_id = str(getattr(request.state, "request_id", "unknown"))
    return {
        "request_id": request_id,
        "chaos_mode": chaos_mode,
    }
