"""Incident narration routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models import NarrateRequest, NarrateResponse
from app.services.minimax_narrator import build_minimax_narrator_from_settings

router = APIRouter(prefix="/incident", tags=["incident"])


@router.post("/narrate", response_model=NarrateResponse)
async def narrate_incident(payload: NarrateRequest) -> NarrateResponse:
    if not settings.enable_minimax_narrator:
        raise HTTPException(status_code=400, detail="Narrator disabled")

    narrator = build_minimax_narrator_from_settings()
    narrative = narrator.narrate(context=payload.context, style=payload.style)

    return NarrateResponse(
        request_id=payload.context.request_id,
        trace_id=payload.context.trace_id,
        narrative=narrative,
    )
