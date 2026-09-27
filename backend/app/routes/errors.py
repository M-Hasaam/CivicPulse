"""Map domain errors to HTTP responses, so services stay free of HTTP."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.services.complaint_service import ComplaintNotFoundError
from app.services.state_machine import InvalidTransitionError


async def _validation_failed(request: Request, exc: Exception) -> JSONResponse:
    """400 with one entry per offending field, instead of FastAPI's default 422."""
    assert isinstance(exc, RequestValidationError)
    errors = [
        {
            # ("body", "text") -> "text"; ("query", "page_size") -> "page_size"
            "field": ".".join(str(part) for part in error["loc"][1:]) or str(error["loc"][0]),
            "in": str(error["loc"][0]),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Validation failed", "errors": errors},
    )


async def _not_found(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})


async def _invalid_transition(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, InvalidTransitionError)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": str(exc),  # the dashboard shows this message verbatim
            "current_status": exc.current.value,
            "attempted_status": exc.target.value,
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _validation_failed)
    app.add_exception_handler(ComplaintNotFoundError, _not_found)
    app.add_exception_handler(InvalidTransitionError, _invalid_transition)
