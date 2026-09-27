import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.logging_config import JsonFormatter, request_id_from_header, request_id_var
from app.main import app

client = TestClient(app)


def test_formatter_writes_one_json_object_with_request_id_and_extras() -> None:
    token = request_id_var.set("abc-123")
    try:
        record = logging.getLogger("t").makeRecord(
            "t", logging.WARNING, __file__, 1, "triage fell back to rules", (), None,
            extra={"complaint_id": "c-1", "provider": "llm:groq", "error_class": "TimeoutError"},
        )
    finally:
        request_id_var.reset(token)
    line = JsonFormatter().format(record)
    entry = json.loads(line)
    assert "\n" not in line
    assert entry["level"] == "WARNING" and entry["message"] == "triage fell back to rules"
    assert entry["request_id"] == "abc-123"
    assert (entry["complaint_id"], entry["provider"], entry["error_class"]) == (
        "c-1", "llm:groq", "TimeoutError",
    )


def test_incoming_request_id_is_propagated_to_the_response_and_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="civicpulse"):
        response = client.get("/health", headers={"X-Request-ID": "req-42"})
    assert response.headers["X-Request-ID"] == "req-42"
    access = [r for r in caplog.records if r.getMessage() == "request completed"]
    assert access and access[-1].request_id == "req-42"  # type: ignore[attr-defined]
    assert access[-1].status == 200 and access[-1].path == "/health"  # type: ignore[attr-defined]


def test_a_request_id_is_generated_when_absent() -> None:
    first = client.get("/health").headers["X-Request-ID"]
    second = client.get("/health").headers["X-Request-ID"]
    assert first and second and first != second


@pytest.mark.parametrize("unsafe", ["x" * 200, 'id"\n{"level": "CRITICAL"}', "a b"])
def test_unsafe_request_ids_are_replaced(unsafe: str) -> None:
    assert request_id_from_header(unsafe) != unsafe


def test_request_id_does_not_leak_outside_the_request() -> None:
    client.get("/health", headers={"X-Request-ID": "req-99"})
    assert request_id_var.get() == "-"


def test_unhandled_exception_still_gets_a_request_id_metric_and_log_line(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A bug we did not anticipate must not escape with none of the observability
    every other response gets - this is what the brief's request_id/log
    requirement is actually protecting against."""

    async def boom() -> None:
        raise RuntimeError("simulated unexpected bug")

    app.add_api_route("/__test_unhandled__", boom)
    try:
        with caplog.at_level(logging.INFO, logger="civicpulse"):
            response = client.get("/__test_unhandled__", headers={"X-Request-ID": "req-boom"})
    finally:
        app.router.routes[:] = [
            r for r in app.router.routes if getattr(r, "path", None) != "/__test_unhandled__"
        ]

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "req-boom"
    assert response.json() == {"detail": "Internal server error"}  # no traceback leaked

    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert errors and errors[-1].request_id == "req-boom"  # type: ignore[attr-defined]
    assert errors[-1].exc_info is not None  # logger.exception captured the traceback

    completed = [r for r in caplog.records if r.getMessage() == "request completed"]
    assert completed[-1].status == 500  # type: ignore[attr-defined]
