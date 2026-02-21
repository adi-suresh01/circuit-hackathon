"""End-to-end demo pipeline routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.models import (
    ExtractResponse,
    PipelineDemoResponse,
    QuoteResponse,
    SubstituteResponse,
    SubstituteResult,
)
from app.routes.graph import graph_service
from app.services.bedrock_vision import (
    PARSE_ERROR_WARNING_PREFIX,
    BedrockBomExtractor,
    BedrockExtractionError,
)
from app.services.suppliers.digikey_quote import quote_bom
from app.state import runtime_state
from app.tracing import tracer

router = APIRouter(prefix="/pipeline", tags=["pipeline"])
extractor = BedrockBomExtractor()


@router.post("/demo", response_model=PipelineDemoResponse)
async def demo_pipeline(
    request: Request,
    image: UploadFile = File(...),
    prefer_in_stock: bool = True,
    exclude_marketplace: bool = True,
    limit: int = 5,
) -> PipelineDemoResponse:
    request_id = str(getattr(request.state, "request_id", "unknown"))
    image_bytes = await image.read()
    image_ext = Path(image.filename or "").suffix.lower().lstrip(".")
    image_format = "jpeg" if image_ext in {"jpg", "jpeg"} else "png"
    limit = max(1, min(limit, 20))

    with tracer.trace("pipeline.demo") as pipeline_span:
        pipeline_span.set_tag("pipeline.request_id", request_id)
        pipeline_span.set_tag("pipeline.image_bytes", len(image_bytes))
        pipeline_span.set_tag("pipeline.image_format", image_format)

        with tracer.trace("bedrock.extract_bom") as extract_span:
            try:
                bom, extract_warnings, model_id = await extractor.extract_bom(
                    image_bytes=image_bytes,
                    filename=image.filename,
                )
            except BedrockExtractionError as exc:
                extract_span.set_tag("bedrock.model_id", "unknown")
                extract_span.set_tag("bom.parse_warnings_count", 1)
                extract_span.set_tag("bom.size", 0)
                extract_span.set_tag("image.bytes", len(image_bytes))
                extract_span.set_tag("image.format", image_format)
                raise HTTPException(status_code=502, detail=str(exc)) from exc

            parse_error = next(
                (
                    warning
                    for warning in extract_warnings
                    if warning.startswith(PARSE_ERROR_WARNING_PREFIX)
                ),
                None,
            )
            extract_span.set_tag("bedrock.model_id", model_id)
            extract_span.set_tag("bom.parse_warnings_count", len(extract_warnings))
            extract_span.set_tag("bom.size", len(bom))
            extract_span.set_tag("image.bytes", len(image_bytes))
            extract_span.set_tag("image.format", image_format)

            if parse_error is not None:
                detail = parse_error.removeprefix(PARSE_ERROR_WARNING_PREFIX).strip()
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to parse Bedrock BOM output: {detail}",
                )

        extract_response = ExtractResponse(
            request_id=request_id,
            bom=bom,
            warnings=extract_warnings,
        )

        chaos_active = runtime_state.is_chaos_mode()
        substitute_results: list[SubstituteResult] = []
        substitute_warnings: list[str] = []
        try:
            for item in bom:
                candidates = graph_service.find_substitutes(item, limit=limit)
                substitute_results.append(
                    SubstituteResult(
                        original=item,
                        candidates=candidates,
                    )
                )
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail="Unable to query substitutes. Verify Neo4j connectivity.",
            ) from exc

        if chaos_active:
            substitute_warnings.append(
                "Chaos mode active: added artificial 1.5s substitute query delay."
            )

        substitutes_response = SubstituteResponse(
            request_id=request_id,
            results=substitute_results,
            warnings=substitute_warnings,
        )

        with tracer.trace("pipeline.quote") as quote_span:
            quote_response: QuoteResponse = await quote_bom(
                bom=bom,
                prefer_in_stock=prefer_in_stock,
                exclude_marketplace=exclude_marketplace,
            )
            quote_response = quote_response.model_copy(update={"request_id": request_id})
            quote_span.set_tag("pipeline.bom_size", len(bom))
            quote_span.set_tag("pipeline.quote_lines", len(quote_response.lines))
            quote_span.set_tag(
                "pipeline.quote_lines_with_chosen",
                sum(1 for line in quote_response.lines if line.chosen is not None),
            )

        total_candidates = sum(len(item.candidates) for item in substitute_results)
        pipeline_warnings = [*extract_warnings, *substitute_warnings, *quote_response.warnings]
        pipeline_span.set_tag("pipeline.bom_size", len(bom))
        pipeline_span.set_tag("pipeline.total_candidates", total_candidates)
        pipeline_span.set_tag("pipeline.quote_lines", len(quote_response.lines))
        pipeline_span.set_tag(
            "pipeline.quote_lines_with_chosen",
            sum(1 for line in quote_response.lines if line.chosen is not None),
        )
        pipeline_span.set_tag("pipeline.warnings_count", len(pipeline_warnings))

    return PipelineDemoResponse(
        request_id=request_id,
        extract=extract_response,
        substitutes=substitutes_response,
        quote=quote_response,
        warnings=pipeline_warnings,
    )
