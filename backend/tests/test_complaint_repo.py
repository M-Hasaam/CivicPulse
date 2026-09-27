"""Mostly no live database here (see PR #20/#25/#27 for that); this pins down
that the locking read really asks Postgres for a row lock and that the lock-
timeout error handling keys on the right exception, since a refactor that
quietly breaks either would otherwise pass every other test untouched."""

import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import DBAPIError

from app.repositories.complaint_repo import ComplaintLockTimeoutError, ComplaintRepository


def test_get_by_id_for_update_locks_the_row() -> None:
    stmt = ComplaintRepository._for_update_statement(uuid.uuid4())
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
    assert "FOR UPDATE" in compiled


def test_get_by_id_has_no_lock() -> None:
    """get_by_id (used for plain reads: GET /api/complaints/{id}, list) must stay
    lock-free - locking every read would serialise unrelated GET requests."""
    import inspect

    from app.repositories.complaint_repo import ComplaintRepository as Repo

    source = inspect.getsource(Repo.get_by_id)
    assert "for_update" not in source.lower()


def _dbapi_error(sqlstate: str | None) -> DBAPIError:
    """A DBAPIError shaped like what asyncpg/SQLAlchemy actually raise: the real
    Postgres error code lives on .orig.sqlstate, not on the exception's own type -
    confirmed live against Postgres 16 (a lock-timeout cancellation surfaces as a
    plain DBAPIError, not OperationalError, with orig.sqlstate == '55P03')."""
    orig = Exception("boom")
    orig.sqlstate = sqlstate  # type: ignore[attr-defined]
    return DBAPIError("SELECT ...", {}, orig)


@pytest.mark.anyio
async def test_get_by_id_for_update_raises_on_lock_timeout_sqlstate() -> None:
    session = AsyncMock()
    session.scalar.side_effect = _dbapi_error("55P03")  # lock_not_available
    repo = ComplaintRepository(session)
    complaint_id = uuid.uuid4()

    with pytest.raises(ComplaintLockTimeoutError) as excinfo:
        await repo.get_by_id_for_update(complaint_id)
    assert excinfo.value.complaint_id == complaint_id
    session.execute.assert_awaited_once()  # the SET LOCAL lock_timeout statement


@pytest.mark.anyio
async def test_get_by_id_for_update_does_not_misclassify_other_db_errors() -> None:
    """An unrelated DBAPIError (wrong SQLSTATE - a dropped connection, a
    constraint violation, division by zero) must propagate as itself, not be
    reported to the client as a retryable lock conflict it never had."""
    session = AsyncMock()
    session.scalar.side_effect = _dbapi_error("22012")  # division_by_zero, unrelated
    repo = ComplaintRepository(session)

    with pytest.raises(DBAPIError):
        await repo.get_by_id_for_update(uuid.uuid4())


@pytest.mark.anyio
async def test_get_by_id_for_update_returns_the_row_when_uncontended() -> None:
    session = AsyncMock()
    session.scalar.return_value = "the-row"
    repo = ComplaintRepository(session)

    assert await repo.get_by_id_for_update(uuid.uuid4()) == "the-row"
