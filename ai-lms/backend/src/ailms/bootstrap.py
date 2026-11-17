"""Runs once before the web server starts: wait for the database and the object
store, create the application's database role, apply migrations, grant the role
its rights, create the bucket, load the sample data if it is missing.

Everything up to the grants runs as the schema owner (ADMIN_DATABASE_URL). The
web server and the worker connect as the application's role (DATABASE_URL),
which has no superuser rights, so PostgreSQL's row-level security applies to it.

    python -m ailms.bootstrap
"""

import logging
import time
from collections.abc import Callable
from pathlib import Path

from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy import Connection, make_url, text

from ailms import seed
from ailms.platform.db import get_admin_engine
from ailms.platform.settings import get_settings
from ailms.platform.storage import get_storage

log = logging.getLogger("ailms.bootstrap")

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _wait_for(name: str, check: Callable[[], object], seconds: int = 90) -> None:
    for attempt in range(seconds):
        try:
            check()
            return
        except Exception as error:  # noqa: BLE001 - any failure means "not ready yet"
            if attempt == seconds - 1:
                raise RuntimeError(f"{name} did not become ready: {error}") from error
            if attempt % 5 == 0:
                log.info("waiting for %s ...", name)
            time.sleep(1)


def _ping_database() -> None:
    with get_admin_engine().connect() as connection:
        connection.execute(text("select 1"))


def migrate() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    command.upgrade(config, "head")


def _app_role() -> tuple[str, str] | None:
    """The application's role and password, or None when it is the schema owner itself."""
    settings = get_settings()
    app = make_url(settings.database_url)
    if not settings.admin_database_url:
        return None
    if make_url(settings.admin_database_url).username == app.username:
        return None
    assert app.username and app.password, "DATABASE_URL needs a user name and a password"
    return app.username, app.password


def _run(connection: Connection, statement: sql.Composable) -> None:
    connection.connection.driver_connection.execute(statement)  # type: ignore[union-attr]


def ensure_app_role(connection: Connection) -> None:
    """Create or update the application's role: may log in, nothing more."""
    role = _app_role()
    if role is None:
        log.warning(
            "the application uses the schema owner's role; row-level security does not apply"
        )
        return
    name, password = role
    exists = connection.execute(
        text("select 1 from pg_roles where rolname = :name"), {"name": name}
    ).first()
    verb = sql.SQL("ALTER ROLE") if exists else sql.SQL("CREATE ROLE")
    _run(
        connection,
        sql.SQL(
            "{} {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS "
            "PASSWORD {}"
        ).format(verb, sql.Identifier(name), sql.Literal(password)),
    )


def grant_app_rights(connection: Connection) -> None:
    """Data rights on every table of the schema, and nothing else (no DDL, no TRUNCATE)."""
    role = _app_role()
    if role is None:
        return
    who = sql.Identifier(role[0])
    for statement in (
        "GRANT USAGE ON SCHEMA public TO {}",
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {}",
        "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {}",
        "REVOKE INSERT, UPDATE, DELETE ON alembic_version FROM {}",
    ):
        _run(connection, sql.SQL(statement).format(who))


def prepare_database() -> None:
    """Role, migrations, rights. Run as the schema owner, under the start-up lock."""
    with get_admin_engine().begin() as connection:
        ensure_app_role(connection)
    migrate()
    with get_admin_engine().begin() as connection:
        grant_app_rights(connection)


# Any fixed number; every container that prepares the database takes this lock first.
_PREPARE_LOCK = 4_171_002_001


def prepare() -> None:
    """Migrate and load the sample data. Safe when two containers start at once."""
    with get_admin_engine().connect() as connection:
        connection.execute(text("select pg_advisory_lock(:key)"), {"key": _PREPARE_LOCK})
        connection.commit()
        try:
            prepare_database()
            log.info("database is up to date")
            _wait_for("the object store", get_storage().ensure_bucket)
            seed.main()
        finally:
            connection.execute(text("select pg_advisory_unlock(:key)"), {"key": _PREPARE_LOCK})
            connection.commit()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    _wait_for("the database", _ping_database)
    prepare()
    log.info("ready")


if __name__ == "__main__":
    main()
