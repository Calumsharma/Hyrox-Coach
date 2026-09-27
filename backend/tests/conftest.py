import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
import app.models  # noqa: F401 — ensures all models are registered on Base.metadata


@pytest.fixture
def db_session():
    # StaticPool is required, not just permissive, for `sqlite:///:memory:`: without it, each
    # thread that checks out a connection gets its OWN private, empty in-memory database (the
    # default pool for `:memory:` is per-thread). FastAPI's TestClient dispatches synchronous
    # route handlers to a worker thread via `anyio.to_thread.run_sync`, so a route hitting this
    # fixture's session from that thread would otherwise see "no such table" errors even though
    # the test's own thread populated the schema correctly — see test_capability_api.py, the
    # first FastAPI TestClient test in this codebase, for where this first surfaced.
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        # Mirrors app/db.py's real engine — SQLite needs this pragma per-connection for FK/
        # ondelete constraints (simple or composite) to actually be enforced.
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
