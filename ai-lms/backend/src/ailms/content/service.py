"""Lessons and their versions. Students only ever get published lessons."""

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ailms.content.document import FORMAT_VERSION, LessonDocument
from ailms.content.models import Lesson, LessonFormat, LessonStatus, LessonVersion
from ailms.platform.audit import record_status_change


@dataclass(frozen=True)
class LessonSummary:
    id: uuid.UUID
    topic_id: uuid.UUID
    format: str
    title: str
    estimated_minutes: int


def published_lesson_summaries(
    session: Session, topic_ids: list[uuid.UUID]
) -> dict[uuid.UUID, LessonSummary]:
    """The published lesson of each topic that has one, keyed by topic.

    Where a topic has both a tutorial and a video, the tutorial is the lesson (ADR 0008 item 9).
    """
    if not topic_ids:
        return {}
    rows = session.execute(
        select(Lesson, LessonVersion)
        .join(LessonVersion, LessonVersion.id == Lesson.published_version_id)
        .where(Lesson.topic_id.in_(topic_ids), Lesson.status == LessonStatus.PUBLISHED.value)
        .order_by(Lesson.created_at)
    ).all()
    out: dict[uuid.UUID, LessonSummary] = {}
    for lesson, version in rows:
        current = out.get(lesson.topic_id)
        if current is None or (
            current.format != LessonFormat.TUTORIAL.value
            and lesson.format == LessonFormat.TUTORIAL.value
        ):
            out[lesson.topic_id] = LessonSummary(
                id=lesson.id,
                topic_id=lesson.topic_id,
                format=lesson.format,
                title=version.title,
                estimated_minutes=version.estimated_minutes,
            )
    return out


def get_lesson_for_reading(
    session: Session, lesson_id: uuid.UUID, *, staff: bool
) -> tuple[Lesson, LessonVersion] | None:
    """The lesson and the version the caller may read, or None.

    A student gets the published version of a published lesson and nothing else.
    Staff also get an unpublished lesson, at its newest version.
    """
    lesson = session.scalar(select(Lesson).where(Lesson.id == lesson_id))
    if lesson is None:
        return None
    published = lesson.status == LessonStatus.PUBLISHED.value and lesson.published_version_id
    if published:
        version = session.scalar(
            select(LessonVersion).where(LessonVersion.id == lesson.published_version_id)
        )
    elif staff:
        version = session.scalar(
            select(LessonVersion)
            .where(LessonVersion.lesson_id == lesson.id)
            .order_by(LessonVersion.number.desc())
            .limit(1)
        )
    else:
        return None
    if version is None:
        return None
    return lesson, version


def import_tutorial(
    session: Session,
    *,
    lesson_id: uuid.UUID,
    version_id: uuid.UUID,
    topic_id: uuid.UUID,
    title: str,
    document: dict[str, Any],
    estimated_minutes: int,
    attribution: str | None,
    publish: bool,
    comment: str | None = None,
) -> Lesson:
    """Store a finished tutorial with fixed ids. Does nothing if the lesson already exists."""
    existing = session.scalar(select(Lesson).where(Lesson.id == lesson_id))
    if existing is not None:
        return existing
    checked = LessonDocument.model_validate(document)
    lesson = Lesson(
        id=lesson_id,
        topic_id=topic_id,
        format=LessonFormat.TUTORIAL.value,
        status=LessonStatus.DRAFT.value,
    )
    session.add(lesson)
    session.flush()
    version = LessonVersion(
        id=version_id,
        lesson_id=lesson_id,
        number=1,
        title=title,
        document=checked.model_dump(mode="json", exclude_none=True),
        format_version=FORMAT_VERSION,
        estimated_minutes=estimated_minutes,
        attribution=attribution,
    )
    session.add(version)
    session.flush()
    record_status_change(
        session, item_kind="lesson", item_id=lesson_id, old_status=None, new_status=lesson.status,
        comment=comment,
    )
    if publish:
        lesson.status = LessonStatus.PUBLISHED.value
        lesson.published_version_id = version_id
        record_status_change(
            session,
            item_kind="lesson",
            item_id=lesson_id,
            old_status=LessonStatus.DRAFT.value,
            new_status=LessonStatus.PUBLISHED.value,
            comment=comment,
        )
    session.flush()
    return lesson
