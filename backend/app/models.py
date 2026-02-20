"""Shared request/response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BomItem(BaseModel):
    refdes: str | None = None
    type: str
    value: str
    package: str | None = None
    qty: int = Field(default=1, ge=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    notes: str | None = None


class ExtractResponse(BaseModel):
    request_id: str
    bom: list[BomItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SubstituteRequest(BaseModel):
    request_id: str | None = None
    bom: list[BomItem]
    constraints: dict[str, Any] | None = None


class SubstituteCandidate(BaseModel):
    mpn: str
    manufacturer: str | None = None
    value: str
    package: str
    score: int = Field(ge=0, le=100)
    reason: str


class SubstituteResult(BaseModel):
    original: BomItem
    candidates: list[SubstituteCandidate] = Field(default_factory=list)


class SubstituteResponse(BaseModel):
    request_id: str
    results: list[SubstituteResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
