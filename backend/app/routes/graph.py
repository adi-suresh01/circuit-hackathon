"""Graph routes."""

from fastapi import APIRouter

from app.models import GraphRequest, GraphResponse

router = APIRouter(prefix="/graph", tags=["graph"])


@router.post("", response_model=GraphResponse)
async def graph(payload: GraphRequest) -> GraphResponse:
    return GraphResponse(
        status="accepted",
        node_count=len(payload.nodes),
        edge_count=len(payload.edges),
    )
