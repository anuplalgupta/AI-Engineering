"""Build checks that run with the tests: module boundaries and the committed API description."""

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_module_boundaries():
    result = subprocess.run(
        ["lint-imports", "--no-cache"], cwd=BACKEND, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_committed_openapi_matches_the_code():
    result = subprocess.run(
        [sys.executable, "-m", "ailms.tools.openapi", "--check"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


MODULES = ["identity", "catalog", "content", "assessment", "learner", "analytics"]


def test_no_api_module_exports_a_table():
    """api.py gives other modules functions and plain data, never ORM classes.

    The import contracts allow `ailms.X -> ailms.Y.api`; if api.py re-exported a table,
    another module could read or change Y's data without Y's rules.
    """
    import importlib
    import inspect

    from sqlalchemy.orm import DeclarativeBase

    for name in MODULES:
        api = importlib.import_module(f"ailms.{name}.api")
        tables = [
            attribute
            for attribute in vars(api).values()
            if inspect.isclass(attribute) and issubclass(attribute, DeclarativeBase)
        ]
        assert tables == [], f"ailms.{name}.api exports tables: {tables}"


def test_migrations_match_the_models():
    """The migrated schema is exactly what the models describe (no forgotten migration)."""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from ailms.platform.db import get_admin_engine
    from ailms.registry import metadata

    def ours(name, type_, parent_names) -> bool:
        return not (type_ == "table" and name is not None and name.startswith("procrastinate_"))

    with get_admin_engine().connect() as connection:
        context = MigrationContext.configure(
            connection, opts={"include_name": ours, "compare_type": True}
        )
        differences = compare_metadata(context, metadata)
    assert differences == []
