"""Extraction routes."""

from fastapi import APIRouter, File, Request, UploadFile

from app.models import BomItem, ExtractResponse

router = APIRouter(prefix="/extract", tags=["extract"])


@router.post("", response_model=ExtractResponse)
async def extract(request: Request, image: UploadFile = File(...)) -> ExtractResponse:
    # Placeholder extraction logic for scaffold.
    _ = image.filename
    request_id = str(getattr(request.state, "request_id", "unknown"))
    return ExtractResponse(
        request_id=request_id,
        bom=[
            BomItem(
                refdes="R1",
                type="resistor",
                value="10k",
                package="0603",
                qty=1,
                confidence=0.82,
                notes="placeholder extracted item",
            )
        ],
        warnings=["placeholder extraction response"],
    )
