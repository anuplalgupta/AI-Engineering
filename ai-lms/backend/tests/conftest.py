"""Test set-up.

The tests never touch the demo database. At start they create a throwaway
database next to it (same server, random name), apply the migrations, and drop
it again at the end. Run them with Docker only:

    docker compose -p ailms -f ai-lms/deploy/compose.yaml run --rm --no-deps backend pytest
"""

import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest
from psycopg import sql

# --- point the application at a throwaway database, before it is imported -----

_BASE_URL = os.environ["DATABASE_URL"]
_TEST_DB = f"ailms_test_{uuid.uuid4().hex[:12]}"


def _with_database(url: str, name: str) -> str:
    return urlunsplit(urlsplit(url)._replace(path=f"/{name}"))


def _libpq(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


os.environ["DATABASE_URL"] = _with_database(_BASE_URL, _TEST_DB)
# Fixed settings, whatever the deployment's .env says. Tests change them with monkeypatch.
os.environ.update(
    {
        "DEMO_MODE": "true",
        "PUBLIC_DEMO": "false",
        "DEMO_ACCESS_CODE": "",
        "SIGNUP_OPEN": "true",
        "TRUSTED_PROXY_HOSTS": '["testclient"]',
    }
)

from ailms.platform import clock as clock_module  # noqa: E402
from ailms.platform import mail, storage  # noqa: E402
from ailms.platform.db import get_engine, scope_to_organisation, session_scope  # noqa: E402
from ailms.platform.settings import Settings, get_settings  # noqa: E402

START = datetime(2026, 11, 16, 9, 0, tzinfo=UTC)


def _admin_connection() -> psycopg.Connection:
    return psycopg.connect(_libpq(_with_database(_BASE_URL, "postgres")), autocommit=True)


@pytest.fixture(scope="session", autouse=True)
def test_database() -> Iterator[str]:
    with _admin_connection() as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(_TEST_DB)))
    try:
        from ailms.bootstrap import migrate

        migrate()
        yield _TEST_DB
    finally:
        get_engine().dispose()
        with _admin_connection() as conn:
            conn.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(_TEST_DB))
            )


def _all_tables() -> list[str]:
    with get_engine().connect() as conn:
        rows = conn.exec_driver_sql(
            "SELECT tablename FROM pg_tables WHERE schemaname = current_schema() "
            "AND tablename <> 'alembic_version' "
            "AND tablename NOT IN ('procrastinate_workers', 'procrastinate_periodic_defers')"
        ).all()
    return [row[0] for row in rows]


@pytest.fixture(autouse=True)
def clean_database(test_database: str) -> Iterator[None]:
    yield
    tables = _all_tables()
    if tables:
        with get_engine().begin() as conn:
            conn.exec_driver_sql(
                "TRUNCATE " + ", ".join(f'"{t}"' for t in tables) + " RESTART IDENTITY CASCADE"
            )


@pytest.fixture(autouse=True)
def clock() -> Iterator[clock_module.FixedClock]:
    fixed = clock_module.FixedClock(START)
    previous = clock_module.get_clock()
    clock_module.set_clock(fixed)
    yield fixed
    clock_module.set_clock(previous)


@pytest.fixture(autouse=True)
def mailer() -> Iterator[mail.RecordingMailer]:
    recording = mail.RecordingMailer()
    mail.set_mailer(recording)
    yield recording
    mail.set_mailer(None)


@pytest.fixture(autouse=True)
def store() -> Iterator[storage.InMemoryStorage]:
    memory = storage.InMemoryStorage()
    storage.set_storage(memory)
    yield memory
    storage.set_storage(None)


@pytest.fixture
def settings() -> Settings:
    return get_settings()


class Orgs:
    """Two organisations loaded from the same sample files, so every row has a twin."""

    def __init__(self, a: uuid.UUID, b: uuid.UUID) -> None:
        self.a = a
        self.b = b


@pytest.fixture
def orgs(store: storage.InMemoryStorage) -> Orgs:
    from ailms.seed import load_sample_data

    with session_scope() as session:
        a = load_sample_data(session, storage=store)
    with session_scope() as session:
        b = load_sample_data(
            session, storage=store, organisation_slug="other", organisation_name="Other Institute"
        )
    return Orgs(a, b)


@pytest.fixture
def app():
    from ailms.main import app as fastapi_app

    return fastapi_app


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client


def sign_in_as(client, organisation_id: uuid.UUID, email: str) -> None:
    """Give the client a session cookie for a user of any organisation."""
    from sqlalchemy import select

    from ailms.identity.api import SESSION_COOKIE, User, start_session

    with session_scope() as session:
        scope_to_organisation(session, organisation_id)
        user = session.scalar(select(User).where(User.email == email))
        assert user is not None, email
        token = start_session(session, user)
    client.cookies.set(SESSION_COOKIE, token)


def demo_login(client, role: str) -> dict:
    response = client.post("/api/auth/demo-login", json={"role": role})
    assert response.status_code == 200, response.text
    return response.json()["user"]
