"""Structured JSON logging configuration."""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    """Inject request_id from contextvars into each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """Simple JSON formatter for structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = getattr(record, "request_id", None)
        if request_id:
            payload["request_id"] = request_id

        dd_trace_id = getattr(record, "dd.trace_id", None)
        dd_span_id = getattr(record, "dd.span_id", None)
        dd_service = getattr(record, "dd.service", None)
        dd_env = getattr(record, "dd.env", None)
        dd_version = getattr(record, "dd.version", None)

        if dd_trace_id is not None:
            payload["dd.trace_id"] = dd_trace_id
        if dd_span_id is not None:
            payload["dd.span_id"] = dd_span_id
        if dd_service is not None:
            payload["dd.service"] = dd_service
        if dd_env is not None:
            payload["dd.env"] = dd_env
        if dd_version is not None:
            payload["dd.version"] = dd_version

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=True)


def configure_logging(level: str = "INFO") -> None:
    """Configure root logger with a JSON stream handler."""

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level.upper())
    root_logger.addHandler(handler)
