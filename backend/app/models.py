"""Shared request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractRequest(BaseModel):
    text: str = Field(..., min_length=1)


class ExtractResponse(BaseModel):
    entities: list[str] = Field(default_factory=list)


class GraphNode(BaseModel):
    id: str
    label: str | None = None


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str | None = None


class GraphRequest(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class GraphResponse(BaseModel):
    status: str = "accepted"
    node_count: int
    edge_count: int
