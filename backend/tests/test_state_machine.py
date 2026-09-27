import pytest

from app.domain import Status
from app.services.state_machine import TRANSITIONS, InvalidTransitionError, ensure_transition

ALLOWED = {
    (Status.open, Status.in_progress),
    (Status.open, Status.rejected),
    (Status.in_progress, Status.resolved),
    (Status.in_progress, Status.rejected),
}


@pytest.mark.parametrize("current", list(Status))
@pytest.mark.parametrize("target", list(Status))
def test_exactly_the_documented_transitions_are_allowed(current: Status, target: Status) -> None:
    if (current, target) in ALLOWED:
        ensure_transition(current, target)
    else:
        with pytest.raises(InvalidTransitionError):
            ensure_transition(current, target)


def test_every_status_has_a_row_and_terminal_states_are_empty() -> None:
    assert set(TRANSITIONS) == set(Status)
    assert TRANSITIONS[Status.resolved] == frozenset()
    assert TRANSITIONS[Status.rejected] == frozenset()


def test_error_names_the_attempted_transition_and_the_options() -> None:
    with pytest.raises(InvalidTransitionError) as excinfo:
        ensure_transition(Status.open, Status.resolved)
    message = str(excinfo.value)
    assert "from 'open' to 'resolved'" in message
    assert "in_progress, rejected" in message


def test_error_says_when_a_status_is_final() -> None:
    with pytest.raises(InvalidTransitionError, match="'resolved' is final"):
        ensure_transition(Status.resolved, Status.open)
