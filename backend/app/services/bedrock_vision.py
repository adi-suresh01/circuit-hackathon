"""Bedrock vision-based BOM extraction service."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.models import BomItem

DEFAULT_BOM_EXTRACTION_PROMPT = (
    "Extract and list all the components from this schematic image of a hardware "
    "diagram. Return ONLY valid JSON array of objects with fields: refdes(optional), "
    "type, value, package(optional), qty(integer). No extra text."
)
PARSE_ERROR_WARNING_PREFIX = "parse_error:"


class BedrockExtractionError(Exception):
    """Raised when Bedrock invocation fails."""


class BedrockBomExtractor:
    """Extract BOM entries from schematic images using Bedrock Converse API."""

    def __init__(
        self,
        *,
        region_name: str | None = None,
        model_id: str | None = None,
        prompt: str | None = None,
    ) -> None:
        self._region_name = region_name or settings.aws_region
        self._model_id = model_id or settings.bedrock_model_id
        self._prompt = prompt or settings.bom_extraction_prompt
        self._runtime_client = boto3.client(
            "bedrock-runtime",
            region_name=self._region_name,
        )

    async def extract_bom(
        self,
        image_bytes: bytes,
        filename: str | None,
    ) -> tuple[list[BomItem], list[str], str]:
        image_format = self._resolve_image_format(filename)
        response = await asyncio.to_thread(
            self._invoke_converse,
            image_bytes=image_bytes,
            image_format=image_format,
        )
        output_text = self._extract_text_content(response)
        return self._parse_bom_output(output_text, self._model_id)

    def _invoke_converse(
        self,
        *,
        image_bytes: bytes,
        image_format: str,
    ) -> dict[str, Any]:
        messages = [
            {
                "role": "user",
                "content": [
                    {"text": self._prompt},
                    {
                        "image": {
                            "format": image_format,
                            "source": {"bytes": image_bytes},
                        }
                    },
                ],
            }
        ]
        try:
            return self._runtime_client.converse(
                modelId=self._model_id,
                messages=messages,
            )
        except (BotoCoreError, ClientError, ValueError) as exc:
            raise BedrockExtractionError(
                f"Bedrock extraction failed: {str(exc) or exc.__class__.__name__}"
            ) from exc

    @staticmethod
    def _resolve_image_format(filename: str | None) -> str:
        if filename:
            suffix = Path(filename).suffix.lower().lstrip(".")
            if suffix in {"jpg", "jpeg"}:
                return "jpeg"
        return "png"

    @staticmethod
    def _extract_text_content(response: dict[str, Any]) -> str:
        output = response.get("output")
        if not isinstance(output, dict):
            raise BedrockExtractionError("Bedrock extraction failed: missing output payload")

        message = output.get("message")
        if not isinstance(message, dict):
            raise BedrockExtractionError("Bedrock extraction failed: missing message payload")

        content = message.get("content")
        if not isinstance(content, list):
            raise BedrockExtractionError("Bedrock extraction failed: missing content payload")

        text_chunks: list[str] = []
        for chunk in content:
            if isinstance(chunk, dict) and isinstance(chunk.get("text"), str):
                text_chunks.append(chunk["text"])

        combined = "\n".join(text_chunks).strip()
        if not combined:
            raise BedrockExtractionError("Bedrock extraction failed: empty model response")
        return combined

    @staticmethod
    def _parse_bom_output(
        output_text: str,
        model_id: str,
    ) -> tuple[list[BomItem], list[str], str]:
        warnings: list[str] = []
        json_array_payload = BedrockBomExtractor._extract_first_json_array(output_text)
        if json_array_payload is None:
            warnings.append(
                f"{PARSE_ERROR_WARNING_PREFIX} model output did not contain a JSON array"
            )
            return [], warnings, model_id

        try:
            parsed_payload = json.loads(json_array_payload)
        except json.JSONDecodeError as exc:
            warnings.append(
                f"{PARSE_ERROR_WARNING_PREFIX} invalid JSON array output: {exc.msg}"
            )
            return [], warnings, model_id

        if not isinstance(parsed_payload, list):
            warnings.append(f"{PARSE_ERROR_WARNING_PREFIX} extracted JSON is not an array")
            return [], warnings, model_id

        bom_items: list[BomItem] = []
        for index, entry in enumerate(parsed_payload):
            if not isinstance(entry, dict):
                warnings.append(f"skipping non-object BOM entry at index {index}")
                continue
            try:
                bom_items.append(BomItem.model_validate(entry))
            except Exception as exc:  # pragma: no cover - defensive validation catch
                warnings.append(f"invalid BOM entry at index {index}: {str(exc)}")

        if not bom_items and parsed_payload:
            warnings.append(
                f"{PARSE_ERROR_WARNING_PREFIX} parsed BOM array but found no valid BOM entries"
            )

        return bom_items, warnings, model_id

    @staticmethod
    def _extract_first_json_array(text: str) -> str | None:
        start = text.find("[")
        if start < 0:
            return None

        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                    continue
                if char == "\\":
                    escaped = True
                    continue
                if char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
                continue
            if char == "[":
                depth += 1
                continue
            if char == "]":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]
        return None
