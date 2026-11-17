"""The job queue's own tables, functions and types (Procrastinate).

The SQL comes from the pinned Procrastinate package. When Procrastinate is
upgraded, its release notes list migration scripts; add them as new revisions.

Revision ID: 0002
Revises: 0001
"""

from alembic import op
from procrastinate.schema import SchemaManager

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def _run(sql: str) -> None:
    # The driver connection runs a multi-statement script as it is, without SQLAlchemy
    # reading ":name" in it as a parameter. It stays inside Alembic's transaction.
    op.get_bind().connection.driver_connection.execute(sql)


def upgrade() -> None:
    _run(SchemaManager.get_schema())


def downgrade() -> None:
    _run(
        """
        DO $$
        DECLARE item record;
        BEGIN
          FOR item IN SELECT tablename FROM pg_tables
                      WHERE schemaname = current_schema() AND tablename LIKE 'procrastinate%' LOOP
            EXECUTE format('DROP TABLE IF EXISTS %I CASCADE', item.tablename);
          END LOOP;
          FOR item IN SELECT p.oid::regprocedure AS signature FROM pg_proc p
                      JOIN pg_namespace n ON n.oid = p.pronamespace
                      WHERE n.nspname = current_schema() AND p.proname LIKE 'procrastinate%' LOOP
            EXECUTE format('DROP FUNCTION IF EXISTS %s CASCADE', item.signature);
          END LOOP;
          FOR item IN SELECT t.typname FROM pg_type t
                      JOIN pg_namespace n ON n.oid = t.typnamespace
                      WHERE n.nspname = current_schema() AND t.typname LIKE 'procrastinate%'
                        AND t.typtype IN ('e', 'c') LOOP
            EXECUTE format('DROP TYPE IF EXISTS %I CASCADE', item.typname);
          END LOOP;
        END $$;
        """
    )
