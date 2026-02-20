"""Datadog tracing helpers and initialization."""

from __future__ import annotations

import os
from typing import Any

try:
    from ddtrace import config as ddtrace_config
    from ddtrace import patch
    from ddtrace import tracer
except Exception:  # pragma: no cover - defensive fallback
    ddtrace_config = None
    patch = None
    tracer = None


def _is_truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class _NoopSpan:
    def __enter__(self) -> "_NoopSpan":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False

    def set_tag(self, key: str, value: Any) -> None:
        _ = (key, value)


class _NoopTracer:
    def trace(self, name: str, service: str | None = None) -> _NoopSpan:
        _ = (name, service)
        return _NoopSpan()

    def current_span(self) -> None:
        return None

    def configure(self, **kwargs: Any) -> None:
        _ = kwargs


if tracer is None:
    tracer = _NoopTracer()

_configured = False


def configure_tracing() -> None:
    """Configure ddtrace patching and runtime options from environment."""

    global _configured
    if _configured:
        return

    trace_enabled = _is_truthy(
        os.getenv("DD_TRACE_ENABLED", os.getenv("DDTRACE_ENABLED", "false"))
    )
    logs_injection = _is_truthy(os.getenv("DD_LOGS_INJECTION", "true"), default=True)

    if patch is not None and trace_enabled:
        patch(fastapi=True, logging=logs_injection)
        if ddtrace_config is not None:
            ddtrace_config.logs_injection = logs_injection

    agent_host = os.getenv("DD_AGENT_HOST")
    if agent_host and hasattr(tracer, "configure"):
        tracer.configure(hostname=agent_host)

    _configured = True


def current_trace_id() -> str:
    """Return the current trace id as a string, or '0' if absent."""

    span = tracer.current_span() if hasattr(tracer, "current_span") else None
    if span is None:
        return "0"

    trace_id = getattr(span, "trace_id", 0) or 0
    return str(trace_id)
