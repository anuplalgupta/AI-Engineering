from alembic import context
from sqlalchemy import create_engine, pool

from ailms.platform.settings import get_settings
from ailms.registry import metadata

target_metadata = metadata


def _is_ours(name, type_, parent_names) -> bool:
    # The job queue's own tables are created by its library, not described in our models.
    return not (type_ == "table" and name is not None and name.startswith("procrastinate_"))


def run_migrations_online() -> None:
    # Migrations run as the schema owner, not as the application's role.
    settings = get_settings()
    url = settings.admin_database_url or settings.database_url
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_name=_is_ours,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise SystemExit("Offline migrations are not supported; run against a database.")
run_migrations_online()
