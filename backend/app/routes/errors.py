"""Map domain errors to HTTP responses, so services stay free of HTTP."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.services.complaint_service import ComplaintNotFoundError
from app.services.state_machine import InvalidTransitionError


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
    app.add_exception_handler(ComplaintNotFoundError, _not_found)
    app.add_exception_handler(InvalidTransitionError, _invalid_transition)
