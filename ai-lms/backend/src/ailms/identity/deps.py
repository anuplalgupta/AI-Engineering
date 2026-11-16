"""FastAPI dependencies: who is calling, and which organisation the request belongs to."""

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ailms.identity import service
from ailms.identity.service import CurrentUser, Role
from ailms.platform.db import get_session, scope_to_organisation
from ailms.platform.settings import get_settings

SESSION_COOKIE = "ailms_session"


def current_user(request: Request, session: Session = Depends(get_session)) -> CurrentUser:
    """The signed-in user. Also ties the database session to that user's organisation."""
    token = request.cookies.get(SESSION_COOKIE)
    user = service.find_session_user(session, token) if token else None
    if user is None:
        raise HTTPException(status_code=401, detail="Please sign in.")
    scope_to_organisation(session, user.organisation_id)
    return user


def require_role(*roles: Role) -> Callable[[CurrentUser], CurrentUser]:
    def check(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Your account cannot do this.")
        return user

    return check


def organisation_session(session: Session = Depends(get_session)) -> Session:
    """For routes used before sign-in: ties the session to this deployment's organisation.

    There is one organisation per deployment for now (ADR 0001 item 6).
    """
    organisation = service.organisation_by_slug(session, get_settings().default_organisation_slug)
    if organisation is None:
        raise HTTPException(status_code=503, detail="The system is not set up yet.")
    scope_to_organisation(session, organisation.id)
    return session
