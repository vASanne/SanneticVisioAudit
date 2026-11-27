"""Structured logging setup. Secret-shaped values are redacted before output."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping, MutableMapping
from typing import Any

import structlog

from app.core.config import get_settings

_SENSITIVE_KEY = re.compile(r"(password|secret|token|api_key|authorization|credential)", re.IGNORECASE)
_URL_USERINFO = re.compile(r"(://[^/\s:@]+:)([^@\s]+)@")
_BEARER = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-+/=]+")
_SESSION_COOKIE = re.compile(r"(?i)((?:visioaudit_session|visioaudit_csrf)=)[^;\s]+")
_ASSIGNMENT = re.compile(r"(?i)(password|secret|token|api_key|authorization)(['\"]?\s*[:=]\s*['\"]?)([^\s,'\"}]+)")
_API_SECRET_HEADER = re.compile(r"(?i)(x-api-secret['\"]?\s*[:=]\s*['\"]?)([^\s,'\"}]+)")
_VAS_SECRET = re.compile(r"\bvas_[A-Za-z0-9_-]{6,}\b")


def setup_logging() -> None:
    """Configure structlog once for the API process or a Celery worker."""

    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(message)s", force=True)
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer() if settings.log_format == "json" else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            _redact,
            renderer,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )


def _redact(_logger: Any, _method: str, event_dict: MutableMapping[str, Any]) -> Mapping[str, Any]:
    for key, value in list(event_dict.items()):
        if isinstance(key, str) and _SENSITIVE_KEY.search(key):
            event_dict[key] = "[redacted]"
        elif isinstance(value, str):
            event_dict[key] = _redact_text(value)
    return event_dict


def _redact_text(value: str) -> str:
    value = _URL_USERINFO.sub(r"\1[redacted]@", value)
    value = _BEARER.sub(r"\1[redacted]", value)
    value = _SESSION_COOKIE.sub(r"\1[redacted]", value)
    value = _API_SECRET_HEADER.sub(r"\1[redacted]", value)
    value = _VAS_SECRET.sub("[redacted]", value)
    return _ASSIGNMENT.sub(r"\1\2[redacted]", value)
