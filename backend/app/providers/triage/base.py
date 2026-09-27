"""The triage contract every provider implements, and the one validator all
model output must pass before the rest of the system sees it."""

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.domain import Category, Priority


class TriageResult(BaseModel):
    # extra="forbid": an unexpected key means the model ignored the schema
    model_config = ConfigDict(extra="forbid")

    category: Category
    priority: Priority
    summary: str = Field(min_length=1, max_length=140)
    # strict: "0.9" or true from a model is malformed output, not something to coerce
    confidence: float = Field(ge=0.0, le=1.0, strict=True)

    @field_validator("summary")
    @classmethod
    def _one_non_blank_line(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("summary is blank")
        if "\n" in value or "\r" in value:
            raise ValueError("summary must be a single line")
        return value


class TriageProvider(Protocol):
    name: str

    async def triage(self, text: str, location: str) -> TriageResult: ...


class TriageError(Exception):
    """Base class: any provider failure. The orchestrator falls back to rules on it."""


class TriageUnavailableError(TriageError):
    """Transient upstream failure (timeout, 429, 5xx). Safe to retry once."""


class TriageRequestError(TriageError):
    """The request itself was rejected (e.g. 400). Retrying would fail the same way."""


class InvalidTriageOutputError(TriageError):
    """The model answered, but not with a valid TriageResult."""


def parse_triage_output(raw: str) -> TriageResult:
    """Validate raw model output against the schema.

    Deliberately strict: prose, code fences, categories outside the enum, a
    summary over 140 characters or extra keys are all rejected rather than
    repaired. Output is only ever parsed as JSON data - never evaluated, never
    interpolated into SQL.
    """
    try:
        # model_validate_json parses and validates in one step, in JSON (strict-aware) mode
        return TriageResult.model_validate_json(raw)
    except ValidationError as exc:
        raise InvalidTriageOutputError(f"{type(exc).__name__}: {exc}") from exc
