import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ailms.catalog import service
from ailms.content.api import published_lesson_summaries
from ailms.identity.api import CurrentUser, ErrorOut, current_user
from ailms.platform.db import get_session

router = APIRouter(tags=["catalog"])


class ProgrammeOut(BaseModel):
    id: uuid.UUID
    title: str


class CourseOut(BaseModel):
    id: uuid.UUID
    title: str
    subject: str
    level: str
    programme: ProgrammeOut


class TopicLessonOut(BaseModel):
    id: uuid.UUID
    format: str
    title: str
    estimated_minutes: int


class TopicOut(BaseModel):
    id: uuid.UUID
    parent_id: uuid.UUID | None
    title: str
    position: int
    lesson: TopicLessonOut | None


@router.get("/courses", responses={401: {"model": ErrorOut}})
def list_courses(
    user: CurrentUser = Depends(current_user), session: Session = Depends(get_session)
) -> list[CourseOut]:
    return [
        CourseOut(
            id=course.id,
            title=course.title,
            subject=course.subject,
            level=course.level,
            programme=ProgrammeOut(id=programme.id, title=programme.title),
        )
        for course, programme in service.list_courses(session)
    ]


@router.get(
    "/courses/{course_id}/topics",
    responses={401: {"model": ErrorOut}, 404: {"model": ErrorOut}},
)
def list_course_topics(
    course_id: uuid.UUID,
    user: CurrentUser = Depends(current_user),
    session: Session = Depends(get_session),
) -> list[TopicOut]:
    """The topic tree as a flat list. A topic carries its lesson only when one is published."""
    if service.get_course(session, course_id) is None:
        raise HTTPException(status_code=404, detail="Course not found.")
    topics = service.list_topics(session, course_id)
    lessons = published_lesson_summaries(session, [topic.id for topic in topics])
    out = []
    for topic in topics:
        lesson = lessons.get(topic.id)
        out.append(
            TopicOut(
                id=topic.id,
                parent_id=topic.parent_id,
                title=topic.title,
                position=topic.position,
                lesson=None
                if lesson is None
                else TopicLessonOut(
                    id=lesson.id,
                    format=lesson.format,
                    title=lesson.title,
                    estimated_minutes=lesson.estimated_minutes,
                ),
            )
        )
    return out
