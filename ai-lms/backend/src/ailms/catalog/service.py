"""Programmes, courses and the topic tree."""

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from ailms.catalog.models import Course, Programme, Topic, TopicPrerequisite


def list_courses(session: Session) -> list[tuple[Course, Programme]]:
    rows = session.execute(
        select(Course, Programme)
        .join(Programme, Programme.id == Course.programme_id)
        .order_by(Programme.title, Course.position, Course.title)
    ).all()
    return [(row[0], row[1]) for row in rows]


def get_course(session: Session, course_id: uuid.UUID) -> Course | None:
    return session.scalar(select(Course).where(Course.id == course_id))


def list_topics(session: Session, course_id: uuid.UUID) -> list[Topic]:
    return list(
        session.scalars(
            select(Topic)
            .where(Topic.course_id == course_id)
            .order_by(Topic.parent_id.is_not(None), Topic.position, Topic.title)
        )
    )


def list_prerequisites(session: Session, course_id: uuid.UUID) -> list[TopicPrerequisite]:
    return list(
        session.scalars(
            select(TopicPrerequisite)
            .join(Topic, Topic.id == TopicPrerequisite.topic_id)
            .where(Topic.course_id == course_id)
        )
    )


@dataclass
class TopicSpec:
    id: uuid.UUID
    title: str
    position: int
    parent_id: uuid.UUID | None = None
    prerequisite_ids: list[uuid.UUID] = field(default_factory=list)


def import_course(
    session: Session,
    *,
    programme_id: uuid.UUID,
    programme_title: str,
    course_id: uuid.UUID,
    course_title: str,
    subject: str,
    level: str,
    topics: list[TopicSpec],
) -> uuid.UUID:
    """Create a programme, a course and its topic tree with fixed ids.

    Anything that already exists is left as it is, so running it twice changes nothing.
    """
    if session.scalar(select(Programme).where(Programme.id == programme_id)) is None:
        session.add(Programme(id=programme_id, title=programme_title))
        session.flush()
    course = get_course(session, course_id)
    if course is None:
        course = Course(
            id=course_id, programme_id=programme_id, title=course_title, subject=subject, level=level
        )
        session.add(course)
        session.flush()

    existing = {topic.id for topic in list_topics(session, course_id)}
    # Parents first, so the parent link always points at a saved row.
    pending = [spec for spec in topics if spec.id not in existing]
    while pending:
        ready = [s for s in pending if s.parent_id is None or s.parent_id in existing]
        if not ready:
            raise ValueError("topic tree has a parent that does not exist")
        for spec in ready:
            session.add(
                Topic(
                    id=spec.id,
                    course_id=course_id,
                    parent_id=spec.parent_id,
                    title=spec.title,
                    position=spec.position,
                )
            )
            existing.add(spec.id)
        session.flush()
        pending = [s for s in pending if s.id not in existing]

    linked = {(p.topic_id, p.prerequisite_id) for p in list_prerequisites(session, course_id)}
    for spec in topics:
        for prerequisite_id in spec.prerequisite_ids:
            if prerequisite_id not in existing:
                raise ValueError("a prerequisite points at a topic that does not exist")
            if (spec.id, prerequisite_id) not in linked:
                session.add(TopicPrerequisite(topic_id=spec.id, prerequisite_id=prerequisite_id))
    session.flush()
    return course.id
