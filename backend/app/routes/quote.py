"""Supplier quoting routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.models import QuoteRequest, QuoteResponse
from app.services.suppliers.digikey_quote import quote_bom

router = APIRouter(prefix="/quote", tags=["quote"])


@router.post("/digikey", response_model=QuoteResponse)
async def quote_digikey(payload: QuoteRequest, request: Request) -> QuoteResponse:
    response = await quote_bom(
        bom=payload.bom,
        prefer_in_stock=payload.prefer_in_stock,
        exclude_marketplace=payload.exclude_marketplace,
    )
    request_id = payload.request_id or str(getattr(request.state, "request_id", "unknown"))
    return response.model_copy(update={"request_id": request_id})
