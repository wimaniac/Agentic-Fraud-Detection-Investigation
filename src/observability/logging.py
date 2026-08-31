"""PII-safe structured logging helpers."""

from __future__ import annotations

import contextvars
import json
import logging
import sys
from typing import Any


request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    """Render operational fields without serializing request bodies or snapshots."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_context.get(),
        }
        for field in ("method", "path", "status_code", "duration_ms", "event"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Configure a single stdout handler once for container log collection."""
    root = logging.getLogger()
    if any(getattr(handler, "_sentinel_json", False) for handler in root.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler._sentinel_json = True  # type: ignore[attr-defined]
    handler.setFormatter(JsonFormatter())
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
