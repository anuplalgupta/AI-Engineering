"""Lessons and their versions. Students only ever get published, not withdrawn, lessons.

Review status belongs to each version. lesson.published_version_id names the version
students see; a newer version can be drafted and reviewed meanwhile without hiding it.
"""

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from ailms.content.document import FORMAT_VERSION, LessonDocument
from ailms.content.models import Lesson, LessonFormat, LessonVersion, VersionStatus
from ailms.platform import clock
from ailms.platform.audit import record_status_change

ITEM_LESSON = "lesson"
ITEM_VERSION = "lesson_version"


@dataclass(frozen=True)
class LessonSummary:
    id: uuid.UUID
    topic_id: uuid.UUID
    format: str
    title: str
    estimated_minutes: int


def _visible_to_students() -> ColumnElement[bool]:
    return Lesson.published_version_id.is_not(None) & Lesson.withdrawn_at.is_(None)


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
        .join(
            LessonVersion,
            (LessonVersion.id == Lesson.published_version_id)
            & (LessonVersion.lesson_id == Lesson.id),
        )
        .where(Lesson.topic_id.in_(topic_ids), _visible_to_students())
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

    A student gets the published version of a lesson that is not withdrawn, and nothing
    else, even while a newer version is in review. Staff get the newest version.
    """
    lesson = session.scalar(select(Lesson).where(Lesson.id == lesson_id))
    if lesson is None:
        return None
    if staff:
        query = select(LessonVersion).order_by(LessonVersion.number.desc()).limit(1)
    elif lesson.published_version_id is not None and lesson.withdrawn_at is None:
        query = select(LessonVersion).where(LessonVersion.id == lesson.published_version_id)
    else:
        return None
    version = session.scalar(query.where(LessonVersion.lesson_id == lesson.id))
    if version is None:
        return None
    return lesson, version


def add_version(
    session: Session,
    *,
    lesson_id: uuid.UUID,
    title: str,
    document: dict[str, Any],
    estimated_minutes: int,
    attribution: str | None,
    version_id: uuid.UUID | None = None,
    comment: str | None = None,
) -> uuid.UUID:
    """Add a new draft version to a lesson. The published version stays as it is."""
    checked = LessonDocument.model_validate(document)
    latest = session.scalar(
        select(func.max(LessonVersion.number)).where(LessonVersion.lesson_id == lesson_id)
    )
    version = LessonVersion(
        id=version_id or uuid.uuid4(),
        lesson_id=lesson_id,
        number=(latest or 0) + 1,
        status=VersionStatus.DRAFT.value,
        title=title,
        document=checked.model_dump(mode="json", exclude_none=True),
        format_version=FORMAT_VERSION,
        estimated_minutes=estimated_minutes,
        attribution=attribution,
    )
    session.add(version)
    session.flush()
    record_status_change(
        session, item_kind=ITEM_VERSION, item_id=version.id, old_status=None,
        new_status=version.status, comment=comment,
    )
    return version.id


def set_version_status(
    session: Session, version_id: uuid.UUID, status: VersionStatus, *, comment: str | None = None
) -> None:
    """Move one version to a new status. Publishing it makes it the version students see."""
    version = session.scalar(select(LessonVersion).where(LessonVersion.id == version_id))
    if version is None:
        raise LookupError("lesson version not found")
    old = version.status
    version.status = status.value
    if status is VersionStatus.PUBLISHED:
        lesson = session.scalar(select(Lesson).where(Lesson.id == version.lesson_id))
        assert lesson is not None
        lesson.published_version_id = version.id
    session.flush()
    record_status_change(
        session, item_kind=ITEM_VERSION, item_id=version.id, old_status=old,
        new_status=status.value, comment=comment,
    )


def withdraw_lesson(session: Session, lesson_id: uuid.UUID, *, comment: str | None = None) -> None:
    """Stop showing a lesson to students (ADR 0008 item 13). Its versions are kept."""
    lesson = session.scalar(select(Lesson).where(Lesson.id == lesson_id))
    if lesson is None:
        raise LookupError("lesson not found")
    if lesson.withdrawn_at is None:
        lesson.withdrawn_at = clock.now()
        session.flush()
        record_status_change(
            session, item_kind=ITEM_LESSON, item_id=lesson.id, old_status="published",
            new_status="withdrawn", comment=comment,
        )


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
) -> uuid.UUID:
    """Store a finished tutorial with fixed ids. Does nothing if the lesson already exists.

    Returns the lesson's id.
    """
    if session.scalar(select(Lesson.id).where(Lesson.id == lesson_id)) is not None:
        return lesson_id
    LessonDocument.model_validate(document)
    session.add(Lesson(id=lesson_id, topic_id=topic_id, format=LessonFormat.TUTORIAL.value))
    session.flush()
    add_version(
        session,
        lesson_id=lesson_id,
        version_id=version_id,
        title=title,
        document=document,
        estimated_minutes=estimated_minutes,
        attribution=attribution,
        comment=comment,
    )
    if publish:
        set_version_status(session, version_id, VersionStatus.PUBLISHED, comment=comment)
    return lesson_id
