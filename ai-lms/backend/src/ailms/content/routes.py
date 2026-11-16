import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ailms.content import service
from ailms.content.document import LessonDocument
from ailms.identity.api import CurrentUser, ErrorOut, Role, current_user
from ailms.platform.db import get_session
from ailms.platform.storage import get_storage, is_valid_media_key, organisation_key

router = APIRouter(tags=["content"])


class LessonOut(BaseModel):
    id: uuid.UUID
    topic_id: uuid.UUID
    title: str
    format: Literal["tutorial"]
    version: int
    estimated_minutes: int
    attribution: str | None
    document: LessonDocument


@router.get(
    "/lessons/{lesson_id}",
    response_model=LessonOut,
    responses={401: {"model": ErrorOut}, 404: {"model": ErrorOut}},
)
def get_lesson(
    lesson_id: uuid.UUID,
    user: CurrentUser = Depends(current_user),
    session: Session = Depends(get_session),
) -> Response:
    """One lesson. A student gets it only if it is published."""
    found = service.get_lesson_for_reading(session, lesson_id, staff=user.role != Role.STUDENT)
    if found is None or found[0].format != "tutorial":
        raise HTTPException(status_code=404, detail="Lesson not found.")
    lesson, version = found
    # The document is sent as stored: fields a section does not use are left out, not null.
    return JSONResponse(
        {
            "id": str(lesson.id),
            "topic_id": str(lesson.topic_id),
            "title": version.title,
            "format": lesson.format,
            "version": version.number,
            "estimated_minutes": version.estimated_minutes,
            "attribution": version.attribution,
            "document": version.document,
        }
    )


@router.get(
    "/media/{key:path}",
    response_class=Response,
    responses={
        200: {"content": {"image/svg+xml": {}, "image/png": {}, "image/jpeg": {}}},
        401: {"model": ErrorOut},
        404: {"model": ErrorOut},
    },
)
def get_media(key: str, user: CurrentUser = Depends(current_user)) -> Response:
    """A stored file, such as a diagram. Only files of the caller's organisation can be reached."""
    if not is_valid_media_key(key):
        raise HTTPException(status_code=404, detail="File not found.")
    stored = get_storage().get(organisation_key(user.organisation_id, key))
    if stored is None:
        raise HTTPException(status_code=404, detail="File not found.")
    return Response(
        content=stored.data,
        media_type=stored.content_type,
        headers={
            "Cache-Control": "private, max-age=3600",
            "X-Content-Type-Options": "nosniff",
            # An SVG opened on its own must not run scripts or load anything.
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
        },
    )
