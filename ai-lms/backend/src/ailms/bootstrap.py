"""Runs once before the web server starts: wait for the database and the object
store, apply migrations, create the bucket, load the sample data if it is missing.

    python -m ailms.bootstrap
"""

import logging
import time
from collections.abc import Callable
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from ailms import seed
from ailms.platform.db import get_engine
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
    with get_engine().connect() as connection:
        connection.execute(text("select 1"))


def migrate() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    command.upgrade(config, "head")


# Any fixed number; every container that prepares the database takes this lock first.
_PREPARE_LOCK = 4_171_002_001


def prepare() -> None:
    """Migrate and load the sample data. Safe when two containers start at once."""
    with get_engine().connect() as connection:
        connection.execute(text("select pg_advisory_lock(:key)"), {"key": _PREPARE_LOCK})
        connection.commit()
        try:
            migrate()
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
