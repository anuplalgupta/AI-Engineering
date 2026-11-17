import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ailms.platform import clock
from ailms.platform.db import Base, OrganisationOwned, new_id


class LessonFormat(StrEnum):
    TUTORIAL = "tutorial"
    UPLOADED_VIDEO = "uploaded_video"
    GENERATED_VIDEO = "generated_video"


class VersionStatus(StrEnum):
    """The review status of one version of a lesson (ADR 0008 section B).

    Each version goes through review on its own, so students keep the approved
    version while an edit is reviewed (ADR 0004 item 16, ADR 0007 item 9).
    """

    DRAFT = "draft"
    RENDERED = "rendered"
    IN_REVIEW = "in_review"
    PUBLISHED = "published"
    REJECTED = "rejected"
    FAILED = "failed"


def _one_of(column: str, values: type[StrEnum]) -> str:
    return f"{column} IN ({', '.join(repr(v.value) for v in values)})"


class Lesson(OrganisationOwned, Base):
    """A lesson of a topic. Students see its published version unless it is withdrawn."""

    __tablename__ = "lesson"
    __table_args__ = (
        CheckConstraint(_one_of("format", LessonFormat), name="format"),
        UniqueConstraint("id", "organisation_id"),
        # The topic belongs to the same organisation.
        ForeignKeyConstraint(
            ["topic_id", "organisation_id"],
            ["topic.id", "topic.organisation_id"],
            ondelete="CASCADE",
        ),
        # The published version is a version of this lesson, in this organisation.
        ForeignKeyConstraint(
            ["published_version_id", "id", "organisation_id"],
            ["lesson_version.id", "lesson_version.lesson_id", "lesson_version.organisation_id"],
            use_alter=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    topic_id: Mapped[uuid.UUID] = mapped_column(index=True)
    format: Mapped[str] = mapped_column(String(30))
    # The version students see. Empty until a version has been approved.
    published_version_id: Mapped[uuid.UUID | None] = mapped_column()
    # Set when an admin withdraws the lesson (ADR 0008 item 13); students then see nothing.
    withdrawn_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=clock.now)


class LessonVersion(OrganisationOwned, Base):
    __tablename__ = "lesson_version"
    __table_args__ = (
        UniqueConstraint("lesson_id", "number"),
        UniqueConstraint("id", "lesson_id", "organisation_id"),
        CheckConstraint(_one_of("status", VersionStatus), name="status"),
        ForeignKeyConstraint(
            ["lesson_id", "organisation_id"],
            ["lesson.id", "lesson.organisation_id"],
            ondelete="CASCADE",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    lesson_id: Mapped[uuid.UUID] = mapped_column(index=True)
    number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default=VersionStatus.DRAFT.value)
    title: Mapped[str] = mapped_column(String(300))
    # The lesson document (ADR 0007 item 3) and the version of its format.
    document: Mapped[dict[str, Any]] = mapped_column(JSONB)
    format_version: Mapped[int] = mapped_column(Integer)
    estimated_minutes: Mapped[int] = mapped_column(Integer)
    attribution: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=clock.now)
