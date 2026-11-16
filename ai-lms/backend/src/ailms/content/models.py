import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ailms.platform import clock
from ailms.platform.db import Base, OrganisationOwned, new_id


class LessonFormat(StrEnum):
    TUTORIAL = "tutorial"
    UPLOADED_VIDEO = "uploaded_video"
    GENERATED_VIDEO = "generated_video"


class LessonStatus(StrEnum):
    """ADR 0008 section B."""

    DRAFT = "draft"
    RENDERED = "rendered"
    IN_REVIEW = "in_review"
    PUBLISHED = "published"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    FAILED = "failed"


class Lesson(OrganisationOwned, Base):
    __tablename__ = "lesson"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    topic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("topic.id", ondelete="CASCADE"), index=True
    )
    format: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default=LessonStatus.DRAFT.value)
    # The version students see. Empty until a version has been approved.
    published_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lesson_version.id", use_alter=True, ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(default=clock.now)


class LessonVersion(OrganisationOwned, Base):
    __tablename__ = "lesson_version"
    __table_args__ = (UniqueConstraint("lesson_id", "number"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lesson.id", ondelete="CASCADE"), index=True
    )
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(300))
    # The lesson document (ADR 0007 item 3) and the version of its format.
    document: Mapped[dict[str, Any]] = mapped_column(JSONB)
    format_version: Mapped[int] = mapped_column(Integer)
    estimated_minutes: Mapped[int] = mapped_column(Integer)
    attribution: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=clock.now)
