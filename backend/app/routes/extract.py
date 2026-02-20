"""Extraction routes."""

from fastapi import APIRouter, File, Request, UploadFile

from app.models import BomItem, ExtractResponse
from app.tracing import tracer

router = APIRouter(prefix="/extract", tags=["extract"])
DEFAULT_BEDROCK_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"


def _extract_bom_with_bedrock_placeholder(
    image_bytes: bytes, filename: str | None
) -> tuple[list[BomItem], list[str], str]:
    _ = image_bytes
    _ = filename

    bom = [
        BomItem(
            refdes="R1",
            type="resistor",
            value="10k",
            package="0603",
            qty=1,
            confidence=0.82,
            notes="placeholder extracted item",
        )
    ]
    warnings = ["placeholder extraction response"]
    return bom, warnings, DEFAULT_BEDROCK_MODEL_ID


@router.post("", response_model=ExtractResponse)
async def extract(request: Request, image: UploadFile = File(...)) -> ExtractResponse:
    image_bytes = await image.read()
    with tracer.trace("bedrock.extract_bom") as span:
        bom, warnings, model_id = _extract_bom_with_bedrock_placeholder(
            image_bytes=image_bytes,
            filename=image.filename,
        )
        span.set_tag("bedrock.model_id", model_id)
        span.set_tag("bom.parse_warnings_count", len(warnings))

    request_id = str(getattr(request.state, "request_id", "unknown"))
    return ExtractResponse(
        request_id=request_id,
        bom=bom,
        warnings=warnings,
    )
