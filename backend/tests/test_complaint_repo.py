"""No live database here (see PR #20/#25 for that); this only pins down that the
locking read really asks Postgres for a row lock, since a refactor that quietly
drops .with_for_update() would otherwise pass every other test untouched."""

import uuid

from app.repositories.complaint_repo import ComplaintRepository


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
