"""JSON logs on stdout, one object per line, each carrying the request id.

stdout, never a file: a container's filesystem is ephemeral and the log shipper
reads stdout. The request id lives in a ContextVar, so every record created
while a request is being handled - in any module - is stamped with it.
"""

import json
import logging
import re
import sys
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# An incoming X-Request-ID is only reused if it looks like an id (no log injection)
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

# Attributes every LogRecord has; anything else was passed via extra= and is logged too
_STANDARD_ATTRS = set(logging.makeLogRecord({}).__dict__) | {
    "message", "asctime", "request_id", "trace_id",
    "color_message",  # uvicorn: the same message with terminal colour codes
}


def request_id_from_header(value: str | None) -> str:
    if value and _SAFE_REQUEST_ID.match(value):
        return value
    return uuid.uuid4().hex


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "trace_id": getattr(record, "trace_id", "-"),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                entry[key] = value
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging(level: str = "INFO") -> None:
    base_factory = logging.getLogRecordFactory()

    def factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = base_factory(*args, **kwargs)
        record.request_id = request_id_var.get()
        # Imported lazily: telemetry.py is not imported at module load time to
        # avoid a circular import (telemetry doesn't need logging_config, but
        # this keeps the dependency direction one-way regardless).
        from app.telemetry import current_trace_id

        record.trace_id = current_trace_id()
        return record

    if not getattr(logging.getLogRecordFactory(), "_civicpulse", False):
        factory._civicpulse = True  # type: ignore[attr-defined]
        logging.setLogRecordFactory(factory)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    # uvicorn's own loggers go through the same JSON handler...
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True
    # ...and its access log is replaced by our request log, which has the request id
    logging.getLogger("uvicorn.access").disabled = True
