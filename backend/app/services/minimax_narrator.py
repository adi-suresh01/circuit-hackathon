"""MiniMax incident narration service."""

from __future__ import annotations

from fastapi import HTTPException
import httpx

from app.config import settings
from app.models import IncidentContext
from app.tracing import tracer


class MiniMaxNarrator:
    """Generates short incident narratives using MiniMax."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model

    @staticmethod
    def _system_prompt(style: str) -> str:
        if style == "oncall":
            return (
                "You are an incident assistant. Return a concise technical summary with: "
                "symptom, likely root cause, and next action. Keep it short and clear."
            )
        return (
            "You are an incident narrator. Produce exactly 3 bullet points: "
            "1) Symptom 2) Likely root cause 3) Next action. "
            "Keep total output under 80 words. Mention trace_id if present."
        )

    @staticmethod
    def _user_prompt(context: IncidentContext, style: str) -> str:
        return (
            f"style={style}\n"
            "Generate an RCA-style narrative from this JSON context:\n"
            f"{context.model_dump_json()}"
        )

    def narrate(self, context: IncidentContext, style: str) -> str:
        url = f"{self._base_url}/v1/text/chatcompletion_v2"
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "name": "System",
                    "content": self._system_prompt(style),
                },
                {
                    "role": "user",
                    "name": "User",
                    "content": self._user_prompt(context, style),
                },
            ],
            "max_completion_tokens": 220,
            "temperature": 0.3,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        with tracer.trace("minimax.narrate") as span:
            span.set_tag("narrator.model", self._model)
            span.set_tag("chaos_mode", context.chaos_mode)
            span.set_tag("endpoint", context.endpoint)

            try:
                with httpx.Client(timeout=20.0) as client:
                    response = client.post(url, json=payload, headers=headers)
            except httpx.RequestError as exc:
                raise HTTPException(
                    status_code=502,
                    detail="MiniMax upstream request failed",
                ) from exc

            if response.status_code >= 400:
                raise HTTPException(
                    status_code=502,
                    detail=f"MiniMax upstream error ({response.status_code})",
                )

            try:
                data = response.json()
            except ValueError as exc:
                raise HTTPException(
                    status_code=502,
                    detail="MiniMax response was not valid JSON",
                ) from exc

            choices = data.get("choices")
            if not isinstance(choices, list) or not choices:
                raise HTTPException(
                    status_code=502,
                    detail="MiniMax response missing choices",
                )

            message = choices[0].get("message", {})
            narrative = message.get("content")
            if not isinstance(narrative, str) or not narrative.strip():
                raise HTTPException(
                    status_code=502,
                    detail="MiniMax response missing narrative content",
                )

            return narrative.strip()


def build_minimax_narrator_from_settings() -> MiniMaxNarrator:
    api_key = (settings.minimax_api_key or "").strip()
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="MINIMAX_API_KEY is not configured",
        )

    return MiniMaxNarrator(
        api_key=api_key,
        base_url=settings.minimax_base_url,
        model=settings.minimax_model,
    )
