"""Extraction routes."""

from fastapi import APIRouter

from app.models import ExtractRequest, ExtractResponse

router = APIRouter(prefix="/extract", tags=["extract"])


@router.post("", response_model=ExtractResponse)
async def extract(payload: ExtractRequest) -> ExtractResponse:
    # Placeholder extraction logic for scaffold.
    _ = payload.text
    return ExtractResponse(entities=[])
