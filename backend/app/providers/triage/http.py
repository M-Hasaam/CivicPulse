"""One outbound call policy for every HTTP triage provider."""

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from app.providers.triage.base import (
    InvalidTriageOutputError,
    TriageRequestError,
    TriageUnavailableError,
)

logger = logging.getLogger(__name__)

Sleep = Callable[[float], Awaitable[None]]

MAX_ATTEMPTS = 2  # the original call plus exactly one retry


def _is_retryable(status: int) -> bool:
    return status == 429 or status >= 500


async def post_json(
    url: str,
    payload: dict[str, Any],
    *,
    provider: str,
    timeout_seconds: float,
    headers: dict[str, str] | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
    sleep: Sleep = asyncio.sleep,
) -> dict[str, Any]:
    """POST JSON and return the decoded body.

    - Every attempt has a hard wall-clock deadline of ``timeout_seconds``. httpx's
      own timeout applies per network operation, so a server trickling bytes could
      otherwise run past it.
    - Timeouts, 429 and 5xx are retried once after a jittered pause.
    - Any other 4xx (a request that is wrong and will stay wrong) is never retried.
    - Connection failures (refused, DNS) are not retried either: an immediate retry
      of a dead host almost never succeeds, and the caller falls back at once.
    - A 2xx whose body is not a JSON object is malformed output, not a crash.

    Headers are never logged - they carry the API key.
    """
    last_error: TriageUnavailableError | None = None
    async with httpx.AsyncClient(timeout=timeout_seconds, transport=transport) as client:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                async with asyncio.timeout(timeout_seconds):
                    response = await client.post(url, json=payload, headers=headers)
            except (TimeoutError, httpx.TimeoutException) as exc:
                last_error = TriageUnavailableError(
                    f"{provider} timed out after {timeout_seconds}s"
                )
                last_error.__cause__ = exc
            except httpx.TransportError as exc:
                raise TriageUnavailableError(
                    f"{provider} unreachable: {type(exc).__name__}"
                ) from exc
            else:
                if response.is_success:
                    try:
                        body = response.json()
                    except ValueError as exc:
                        raise InvalidTriageOutputError(
                            f"{provider} returned a non-JSON body"
                        ) from exc
                    if not isinstance(body, dict):
                        raise InvalidTriageOutputError(
                            f"{provider} returned {type(body).__name__}, not an object"
                        )
                    return body
                if not _is_retryable(response.status_code):
                    raise TriageRequestError(
                        f"{provider} rejected the request: HTTP {response.status_code}"
                    )
                last_error = TriageUnavailableError(
                    f"{provider} returned HTTP {response.status_code}"
                )

            if attempt < MAX_ATTEMPTS:
                pause = random.uniform(0.5, 1.5)
                logger.warning(
                    "%s attempt %d failed (%s); retrying in %.2fs",
                    provider, attempt, last_error, pause,
                )
                await sleep(pause)

    assert last_error is not None
    raise last_error
