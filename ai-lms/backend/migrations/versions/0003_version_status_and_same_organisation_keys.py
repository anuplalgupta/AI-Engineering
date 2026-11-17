"""Review status per lesson version; links between rows stay inside one organisation.

* lesson_version.status replaces lesson.status, so an edit can be reviewed while
  students keep the published version (ADR 0004 item 16, ADR 0007 item 9).
  lesson.withdrawn_at records a withdrawal (ADR 0008 item 13).
* Every foreign key between organisation-owned tables includes organisation_id,
  and lesson.published_version_id must be a version of that same lesson.
* client_rate_event counts sign-in requests per client address.

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

VERSION_STATUSES = ("draft", "rendered", "in_review", "published", "rejected", "failed")

# (table, columns, referred table, referred columns, ondelete); names are kept from 0001.
OLD_KEYS = [
    ("course", ["programme_id"], "programme", ["id"], "CASCADE"),
    ("topic", ["course_id"], "course", ["id"], "CASCADE"),
    ("topic", ["parent_id"], "topic", ["id"], "CASCADE"),
    ("topic_prerequisite", ["topic_id"], "topic", ["id"], "CASCADE"),
    ("topic_prerequisite", ["prerequisite_id"], "topic", ["id"], "CASCADE"),
    ("lesson", ["topic_id"], "topic", ["id"], "CASCADE"),
    ("lesson_version", ["lesson_id"], "lesson", ["id"], "CASCADE"),
    ("user_session", ["user_id"], "user_account", ["id"], "CASCADE"),
]
PARENTS = ["programme", "course", "topic", "lesson", "user_account"]


def _fk_name(table: str, column: str, referred: str) -> str:
    return f"fk_{table}_{column}_{referred}"


def upgrade() -> None:
    # --- review status moves from the lesson to each version ---------------------------
    op.add_column(
        "lesson_version",
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
    )
    op.add_column("lesson", sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        """
        UPDATE lesson_version v SET status = 'published'
        FROM lesson l WHERE l.published_version_id = v.id
        """
    )
    # A lesson in review, rejected or failed: that status belonged to its newest version.
    op.execute(
        """
        UPDATE lesson_version v SET status = l.status
        FROM lesson l
        WHERE v.lesson_id = l.id
          AND l.status IN ('rendered', 'in_review', 'rejected', 'failed')
          AND v.number = (SELECT max(number) FROM lesson_version w WHERE w.lesson_id = l.id)
          AND v.id IS DISTINCT FROM l.published_version_id
        """
    )
    op.execute("UPDATE lesson SET withdrawn_at = now() WHERE status = 'withdrawn'")
    # Students now see any lesson with a published version; keep hidden what was hidden.
    op.execute(
        "UPDATE lesson SET published_version_id = NULL "
        "WHERE status NOT IN ('published', 'withdrawn')"
    )
    op.alter_column("lesson_version", "status", server_default=None)
    op.create_check_constraint(
        op.f("ck_lesson_version_status"),
        "lesson_version",
        "status IN (" + ", ".join(f"'{s}'" for s in VERSION_STATUSES) + ")",
    )
    op.drop_constraint(op.f("ck_lesson_status"), "lesson", type_="check")
    op.drop_column("lesson", "status")

    # --- links stay inside one organisation ---------------------------------------------
    op.drop_constraint(
        op.f("fk_lesson_published_version_id_lesson_version"), "lesson", type_="foreignkey"
    )
    for table, columns, referred, _, _ in OLD_KEYS:
        op.drop_constraint(op.f(_fk_name(table, columns[0], referred)), table, type_="foreignkey")
    for table in PARENTS:
        op.create_unique_constraint(op.f(f"uq_{table}_id"), table, ["id", "organisation_id"])
    op.create_unique_constraint(
        op.f("uq_lesson_version_id"), "lesson_version", ["id", "lesson_id", "organisation_id"]
    )
    for table, columns, referred, referred_columns, ondelete in OLD_KEYS:
        op.create_foreign_key(
            op.f(_fk_name(table, columns[0], referred)),
            table,
            referred,
            [*columns, "organisation_id"],
            [*referred_columns, "organisation_id"],
            ondelete=ondelete,
        )
    op.create_foreign_key(
        op.f("fk_lesson_published_version_id_lesson_version"),
        "lesson",
        "lesson_version",
        ["published_version_id", "id", "organisation_id"],
        ["id", "lesson_id", "organisation_id"],
    )

    # --- counting sign-in requests per client address ------------------------------------
    op.create_table(
        "client_rate_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("client_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_client_rate_event")),
    )
    op.create_index(
        op.f("ix_client_rate_event_action"),
        "client_rate_event",
        ["action", "client_hash", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_client_rate_event_action"), table_name="client_rate_event")
    op.drop_table("client_rate_event")

    op.drop_constraint(
        op.f("fk_lesson_published_version_id_lesson_version"), "lesson", type_="foreignkey"
    )
    for table, columns, referred, _, _ in OLD_KEYS:
        op.drop_constraint(op.f(_fk_name(table, columns[0], referred)), table, type_="foreignkey")
    op.drop_constraint(op.f("uq_lesson_version_id"), "lesson_version", type_="unique")
    for table in PARENTS:
        op.drop_constraint(op.f(f"uq_{table}_id"), table, type_="unique")
    for table, columns, referred, referred_columns, ondelete in OLD_KEYS:
        op.create_foreign_key(
            op.f(_fk_name(table, columns[0], referred)),
            table, referred, columns, referred_columns, ondelete=ondelete,
        )
    op.create_foreign_key(
        op.f("fk_lesson_published_version_id_lesson_version"),
        "lesson", "lesson_version", ["published_version_id"], ["id"], ondelete="SET NULL",
    )

    op.add_column(
        "lesson",
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
    )
    op.execute(
        "UPDATE lesson SET status = CASE WHEN withdrawn_at IS NOT NULL THEN 'withdrawn' "
        "WHEN published_version_id IS NOT NULL THEN 'published' ELSE 'draft' END"
    )
    op.alter_column("lesson", "status", server_default=None)
    op.create_check_constraint(
        op.f("ck_lesson_status"),
        "lesson",
        "status IN ('draft', 'rendered', 'in_review', 'published', 'rejected', 'withdrawn', "
        "'failed')",
    )
    op.drop_column("lesson", "withdrawn_at")
    op.drop_constraint(op.f("ck_lesson_version_status"), "lesson_version", type_="check")
    op.drop_column("lesson_version", "status")
