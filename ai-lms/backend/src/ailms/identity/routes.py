import uuid
from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ailms.identity import service, tasks
from ailms.identity.deps import SESSION_COOKIE, current_user, organisation_session
from ailms.identity.service import AccessCodeError, CurrentUser, Role, SignInError
from ailms.platform import ratelimit
from ailms.platform.db import current_organisation_id, get_session
from ailms.platform.settings import get_settings

router = APIRouter(tags=["identity"])


class OrganisationOut(BaseModel):
    id: uuid.UUID
    name: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: Literal["admin", "reviewer", "student"]
    organisation: OrganisationOut


class SignedInOut(BaseModel):
    user: UserOut


class RequestCodeIn(BaseModel):
    email: str = Field(max_length=254)


class VerifyCodeIn(BaseModel):
    email: str = Field(max_length=254)
    code: str = Field(max_length=12)


class DemoLoginIn(BaseModel):
    role: Literal["admin", "reviewer", "student"]
    access_code: str | None = Field(default=None, max_length=200)


class ErrorOut(BaseModel):
    detail: str


def _user_out(user: CurrentUser) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role.value,
        organisation=OrganisationOut(id=user.organisation_id, name=user.organisation_name),
    )


def _set_cookie(request: Request, response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=get_settings().session_days * 24 * 3600,
        path="/",
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )


_TOO_MANY = "Too many requests from this address. Please wait a while and try again."


def _client(request: Request) -> str:
    # Behind the web server this is the browser's address (see platform/proxy.py).
    return request.client.host if request.client else "unknown"


def _check_client_rate(
    session: Session, request: Request, action: str, limit: int
) -> None:
    allowed = ratelimit.allow(
        session, action=action, client=_client(request), limit=limit, window=timedelta(hours=1)
    )
    if not allowed:
        session.commit()
        raise HTTPException(status_code=429, detail=_TOO_MANY)


@router.post(
    "/auth/request-code",
    status_code=204,
    responses={422: {"model": ErrorOut}, 429: {"model": ErrorOut}},
)
def request_code(
    body: RequestCodeIn, request: Request, session: Session = Depends(organisation_session)
) -> None:
    """Email a one-time sign-in code. Always 204, whether or not the account exists.

    The request only puts a job on the queue; the worker decides whether to send, so the
    answer takes the same time for a known and an unknown address.
    """
    try:
        email = service.normalise_email(body.email)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    _check_client_rate(
        session, request, "request-code", get_settings().client_max_code_requests_per_hour
    )
    tasks.send_sign_in_code.defer(
        organisation_id=str(current_organisation_id(session)), email=email
    )
    session.commit()


@router.post("/auth/verify-code", responses={400: {"model": ErrorOut}, 429: {"model": ErrorOut}})
def verify_code(
    body: VerifyCodeIn,
    request: Request,
    response: Response,
    session: Session = Depends(organisation_session),
) -> SignedInOut:
    _check_client_rate(
        session, request, "verify-code", get_settings().client_max_code_checks_per_hour
    )
    try:
        user = service.verify_code(session, body.email, body.code)
    except SignInError:
        # Keep the failed-attempt count even though the request fails.
        session.commit()
        raise HTTPException(
            status_code=400, detail="That code is wrong or has expired. Ask for a new one."
        ) from None
    _set_cookie(request, response, service.start_session(session, user))
    out = SignedInOut(user=_user_out(service.current_user_for(session, user)))
    # Commit before answering, so the very next request finds the session.
    session.commit()
    return out


@router.post(
    "/auth/demo-login", responses={403: {"model": ErrorOut}, 404: {"model": ErrorOut}}
)
def demo_login(
    body: DemoLoginIn,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
) -> SignedInOut:
    """Enter as a demo account. Exists only when demo mode is on (ADR 0008 section G)."""
    if not get_settings().demo_mode:
        raise HTTPException(status_code=404, detail="Not Found")
    session = organisation_session(session)
    try:
        user = service.demo_user(session, Role(body.role), body.access_code)
    except AccessCodeError:
        raise HTTPException(status_code=403, detail="That access code is not right.") from None
    if user is None:
        raise HTTPException(status_code=404, detail="There is no demo account for that role.")
    _set_cookie(request, response, service.start_session(session, user))
    out = SignedInOut(user=_user_out(service.current_user_for(session, user)))
    # Commit before answering, so the very next request finds the session.
    session.commit()
    return out


@router.post("/auth/logout", status_code=204)
def logout(
    request: Request, response: Response, session: Session = Depends(get_session)
) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        service.end_session(session, token)
        session.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", responses={401: {"model": ErrorOut}})
def me(user: CurrentUser = Depends(current_user)) -> UserOut:
    return _user_out(user)
