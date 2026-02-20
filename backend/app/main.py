"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from uuid import uuid4

from app.tracing import configure_tracing, current_trace_id

configure_tracing()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.logging_config import configure_logging, request_id_ctx_var
from app.routes import extract, graph, health

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id

    token = request_id_ctx_var.set(request_id)
    try:
        response = await call_next(request)
    finally:
        request_id_ctx_var.reset(token)

    response.headers["X-Request-ID"] = request_id
    response.headers["x-trace-id"] = current_trace_id()
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


app.include_router(health.router)
app.include_router(extract.router)
app.include_router(graph.router)


@app.on_event("shutdown")
def shutdown_event() -> None:
    graph.close_graph_service()
