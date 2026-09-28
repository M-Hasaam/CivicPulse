"""Deterministic stand-in for an LLM, used in CI and tests.

Same input + same seed -> same output, with no network. Failure injection lets
tests drive every error path the real providers can hit.
"""

import hashlib
import random
from typing import Literal

from app.providers.triage.base import (
    TriageResult,
    TriageUnavailableError,
    parse_triage_output,
)
from app.providers.triage.rules import RuleBasedTriage

FailureMode = Literal["none", "raise", "malformed"]

# What a misbehaving model really sends back: prose around a fenced block
MALFORMED_OUTPUT = 'Sure! Here is the triage:\n```json\n{"category": "flood"}\n```'


class SimulatedTriage:
    name = "simulated"

    def __init__(self, failure: FailureMode = "none", seed: int = 0) -> None:
        self.failure = failure
        self.seed = seed
        self._classifier = RuleBasedTriage()

    async def triage(self, text: str, location: str) -> TriageResult:
        if self.failure == "raise":
            raise TriageUnavailableError("simulated upstream failure (503)")
        if self.failure == "malformed":
            # Goes through the real validator, so tests exercise the real rejection path
            return parse_triage_output(MALFORMED_OUTPUT)

        digest = hashlib.sha256(f"{self.seed}:{text}".encode()).digest()
        rng = random.Random(digest)
        base = await self._classifier.triage(text, location)
        summary = f"[sim] {base.summary}"
        return TriageResult(
            category=base.category,
            priority=base.priority,
            summary=summary if len(summary) <= 140 else summary[:137] + "...",
            confidence=round(rng.uniform(0.7, 0.99), 2),
        )
