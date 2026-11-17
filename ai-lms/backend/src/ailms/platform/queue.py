"""The job queue: Procrastinate, stored in PostgreSQL (ADR 0002).

The worker runs:  procrastinate --app=ailms.worker.app worker  (ailms/worker.py registers every job)
"""

import uuid
from datetime import datetime

from procrastinate import App, PsycopgConnector
from sqlalchemy import select
from sqlalchemy.orm import Mapped, mapped_column

from ailms.platform import clock
from ailms.platform.db import Base, session_scope
from ailms.platform.settings import get_settings


def _conninfo() -> str:
    # SQLAlchemy writes the driver into the URL; libpq does not accept that.
    return get_settings().database_url.replace("postgresql+psycopg://", "postgresql://", 1)


app = App(connector=PsycopgConnector(conninfo=_conninfo()))


class JobPing(Base):
    """One row for each ping job that has run. Proves the worker is alive."""

    __tablename__ = "job_ping"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    ran_at: Mapped[datetime] = mapped_column()


@app.task(name="ping", queue="default")
def ping(token: str) -> None:
    # Safe to run twice: the second run finds the row and leaves it alone.
    with session_scope() as session:
        if session.get(JobPing, uuid.UUID(token)) is None:
            session.add(JobPing(id=uuid.UUID(token), ran_at=clock.now()))


def enqueue_ping() -> uuid.UUID:
    token = uuid.uuid4()
    ping.defer(token=str(token))
    return token


def ping_ran_at(token: uuid.UUID) -> datetime | None:
    with session_scope() as session:
        return session.scalar(select(JobPing.ran_at).where(JobPing.id == token))
