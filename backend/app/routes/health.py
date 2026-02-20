"""Health check routes."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from neo4j import GraphDatabase

from app.config import settings

router = APIRouter(tags=["health"])
READINESS_TIMEOUT_SECONDS = 1.0


def _check_neo4j_connectivity() -> bool:
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password),
        connection_timeout=READINESS_TIMEOUT_SECONDS,
        connection_acquisition_timeout=READINESS_TIMEOUT_SECONDS,
        max_connection_pool_size=1,
    )
    try:
        driver.verify_connectivity()
        with driver.session() as session:
            session.run("RETURN 1 AS ok").consume()
        return True
    except Exception:
        return False
    finally:
        driver.close()


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready_check() -> JSONResponse:
    if _check_neo4j_connectivity():
        return JSONResponse(status_code=200, content={"status": "ready"})
    return JSONResponse(
        status_code=503,
        content={"status": "not_ready", "neo4j": "unavailable"},
    )
