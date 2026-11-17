"""Row-level security on every organisation-owned table (ADR 0001 item 6, second layer).

The application sets ailms.organisation_id (and ailms.system inside system_scope())
at the start of each transaction; see platform/db.py. A row is visible and writable
only when it belongs to that organisation. The schema owner, used for migrations,
is not subject to these policies; the application's role is.

Revision ID: 0004
Revises: 0003
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

OWNED_TABLES = [
    "programme",
    "course",
    "topic",
    "topic_prerequisite",
    "lesson",
    "lesson_version",
    "user_account",
    "user_session",
    "login_code",
    "status_change",
]

RULE = (
    "current_setting('ailms.system', true) = 'on' "
    "OR organisation_id = NULLIF(current_setting('ailms.organisation_id', true), '')::uuid"
)


def upgrade() -> None:
    for table in OWNED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY organisation_isolation ON {table} USING ({RULE}) WITH CHECK ({RULE})"
        )


def downgrade() -> None:
    for table in OWNED_TABLES:
        op.execute(f"DROP POLICY IF EXISTS organisation_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
