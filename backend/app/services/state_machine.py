"""Complaint status lifecycle as data: the table is the rule."""

from types import MappingProxyType

from app.domain import Status

# Every allowed move, and nothing else. resolved and rejected are terminal.
TRANSITIONS = MappingProxyType(
    {
        Status.open: frozenset({Status.in_progress, Status.rejected}),
        Status.in_progress: frozenset({Status.resolved, Status.rejected}),
        Status.resolved: frozenset(),
        Status.rejected: frozenset(),
    }
)


class InvalidTransitionError(Exception):
    def __init__(self, current: Status, target: Status) -> None:
        self.current = current
        self.target = target
        allowed = sorted(s.value for s in TRANSITIONS[current])
        allowed_text = ", ".join(allowed) if allowed else f"none ('{current.value}' is final)"
        super().__init__(
            f"Cannot change status from '{current.value}' to '{target.value}'. "
            f"Allowed from '{current.value}': {allowed_text}."
        )


def ensure_transition(current: Status, target: Status) -> None:
    """Raise InvalidTransitionError unless the table allows current -> target."""
    if target not in TRANSITIONS[current]:
        raise InvalidTransitionError(current, target)
