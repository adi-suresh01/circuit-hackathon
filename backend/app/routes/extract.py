"""Extraction routes."""

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.config import settings
from app.models import ExtractResponse
from app.services.bedrock_vision import (
    PARSE_ERROR_WARNING_PREFIX,
    BedrockBomExtractor,
    BedrockExtractionError,
)
from app.tracing import tracer

router = APIRouter(prefix="/extract", tags=["extract"])
extractor = BedrockBomExtractor()


@router.post("", response_model=ExtractResponse)
async def extract(request: Request, image: UploadFile = File(...)) -> ExtractResponse:
    image_bytes = await image.read()
    image_ext = Path(image.filename or "").suffix.lower().lstrip(".")
    image_format = "jpeg" if image_ext in {"jpg", "jpeg"} else "png"
    with tracer.trace("bedrock.extract_bom") as span:
        model_id = settings.bedrock_model_id
        try:
            bom, warnings, model_id = await extractor.extract_bom(
                image_bytes=image_bytes,
                filename=image.filename,
            )
        except BedrockExtractionError as exc:
            span.set_tag("bedrock.model_id", model_id)
            span.set_tag("bom.parse_warnings_count", 1)
            span.set_tag("bom.size", 0)
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        parse_error = next(
            (
                warning
                for warning in warnings
                if warning.startswith(PARSE_ERROR_WARNING_PREFIX)
            ),
            None,
        )
        span.set_tag("bedrock.model_id", model_id)
        span.set_tag("bom.parse_warnings_count", len(warnings))
        span.set_tag("bom.size", len(bom))
        span.set_tag("image.bytes", len(image_bytes))
        span.set_tag("image.format", image_format)

        if parse_error is not None:
            detail = parse_error.removeprefix(PARSE_ERROR_WARNING_PREFIX).strip()
            raise HTTPException(
                status_code=502,
                detail=f"Failed to parse Bedrock BOM output: {detail}",
            )

    request_id = str(getattr(request.state, "request_id", "unknown"))
    return ExtractResponse(
        request_id=request_id,
        bom=bom,
        warnings=warnings,
    )
