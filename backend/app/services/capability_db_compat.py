"""Dialect-aware idempotent insert — Program Engine v5 Milestone 2, §D5/§J point 1.

The only file in this milestone that imports a dialect-specific SQLAlchemy insert construct.
Every capability service calls `idempotent_insert` instead of building its own `INSERT ...
ON CONFLICT` statement, so switching the deployed database to PostgreSQL later touches this one
file, not every capability service.

No live PostgreSQL instance is available in this environment — the PostgreSQL branch below is
exercised only by `compile_postgresql_statement`'s compile-only test, never against a real
PostgreSQL connection. See the Milestone 2 v2.2 plan, §D5, for this honestly-disclosed limit.
"""

from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy.dialects import postgresql as postgresql_dialect_module
from sqlalchemy.dialects.postgresql import insert as _postgresql_insert
from sqlalchemy.dialects.sqlite import insert as _sqlite_insert
from sqlalchemy.orm import Session


class UnsupportedDialectError(RuntimeError):
    """Raised when `idempotent_insert` is called against a database dialect this module has no
    conflict-handling statement for. Deliberately fails loudly rather than silently falling
    back to a check-then-insert race."""


def idempotent_insert(
    session: Session,
    model: type,
    values: dict[str, Any],
    conflict_columns: Sequence[str] = ("id",),
):
    """Inserts `values` into `model`'s table, doing nothing if a row already conflicts on
    `conflict_columns`, then returns the persisted row — whether this call's insert won or lost
    the race.

    Never assumes the caller's in-memory values are what got persisted: after the statement
    executes, the row is always re-fetched from the database. `ON CONFLICT DO NOTHING` means a
    losing insert never raises `IntegrityError` and needs no rollback/retry — the statement
    itself no-ops. **This operates entirely inside the caller's existing transaction — it never
    calls `commit()` or `rollback()` itself.** The caller (e.g. the `/capabilities/recompute`
    route) owns the transaction boundary: it commits once, after every step of a multi-step
    workflow succeeds, so a genuine failure partway through rolls back everything this helper
    did earlier in the same request, not just the step that failed. A genuine, unrelated
    `IntegrityError` (e.g. a composite-FK violation) is never caught here, so it propagates
    normally rather than being mistaken for an idempotency case.
    """

    dialect = session.get_bind().dialect.name
    table = model.__table__
    conflict_columns = list(conflict_columns)

    if dialect == "sqlite":
        stmt = _sqlite_insert(table).values(**values).on_conflict_do_nothing(index_elements=conflict_columns)
    elif dialect == "postgresql":
        stmt = _postgresql_insert(table).values(**values).on_conflict_do_nothing(index_elements=conflict_columns)
    else:
        raise UnsupportedDialectError(
            f"idempotent_insert has no conflict-handling statement for dialect {dialect!r}"
        )

    session.execute(stmt)
    session.flush()

    if conflict_columns == ["id"]:
        return session.get(model, values["id"])
    filters = [getattr(model, col) == values[col] for col in conflict_columns]
    return session.query(model).filter(*filters).first()


def compile_postgresql_statement(model: type, values: dict[str, Any], conflict_columns: Sequence[str] = ("id",)) -> str:
    """Compiles (never executes) the PostgreSQL branch of `idempotent_insert`'s statement, for
    the compile-only test this milestone relies on in place of a live PostgreSQL integration
    test — see the module docstring's disclosed limitation."""

    table = model.__table__
    stmt = _postgresql_insert(table).values(**values).on_conflict_do_nothing(index_elements=list(conflict_columns))
    return str(stmt.compile(dialect=postgresql_dialect_module.dialect()))
