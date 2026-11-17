"""Sign-in by email one-time code, demo entry, and sessions kept in the database."""

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ailms.identity.models import LoginCode, Organisation, User, UserSession
from ailms.platform import clock, security
from ailms.platform.db import system_scope
from ailms.platform.mail import get_mailer
from ailms.platform.settings import get_settings

log = logging.getLogger(__name__)

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Role(StrEnum):
    ADMIN = "admin"
    REVIEWER = "reviewer"
    STUDENT = "student"


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    email: str
    display_name: str
    role: Role
    organisation_id: uuid.UUID
    organisation_name: str


class SignInError(Exception):
    pass


class AccessCodeError(Exception):
    pass


def normalise_email(raw: str) -> str:
    email = raw.strip().lower()
    if len(email) > 254 or not _EMAIL.match(email):
        raise ValueError("That does not look like an email address.")
    return email


def organisation_by_slug(session: Session, slug: str) -> Organisation | None:
    return session.scalar(select(Organisation).where(Organisation.slug == slug))


def organisation_id_by_slug(session: Session, slug: str) -> uuid.UUID | None:
    return session.scalar(select(Organisation.id).where(Organisation.slug == slug))


def any_organisation_exists(session: Session) -> bool:
    return session.scalar(select(Organisation.id).limit(1)) is not None


def ensure_organisation(
    session: Session, *, organisation_id: uuid.UUID, slug: str, name: str
) -> uuid.UUID:
    """Create the organisation if it does not exist. Returns its id."""
    if session.get(Organisation, organisation_id) is None:
        session.add(Organisation(id=organisation_id, slug=slug, name=name))
        session.flush()
    return organisation_id


def ensure_user(
    session: Session,
    *,
    email: str,
    display_name: str,
    role: Role,
    is_demo: bool = False,
    user_id: uuid.UUID | None = None,
) -> uuid.UUID:
    """Create the user in the session's organisation if the email is new. Returns the user's id."""
    email = normalise_email(email)
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, display_name=display_name, role=role.value, is_demo=is_demo)
        if user_id is not None:
            user.id = user_id
        session.add(user)
        session.flush()
    return user.id


def _to_current(user: User, organisation: Organisation) -> CurrentUser:
    return CurrentUser(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=Role(user.role),
        organisation_id=organisation.id,
        organisation_name=organisation.name,
    )


def current_user_for(session: Session, user: User) -> CurrentUser:
    organisation = session.get(Organisation, user.organisation_id)
    assert organisation is not None
    return _to_current(user, organisation)


# --- one-time codes ---------------------------------------------------------


def _failures_since(session: Session, email: str, since: datetime) -> int:
    return session.scalar(
        select(func.coalesce(func.sum(LoginCode.attempts), 0)).where(
            LoginCode.email == email, LoginCode.created_at > since
        )
    ) or 0


def is_locked_out(session: Session, email: str) -> bool:
    """Too many wrong codes for this email in the lockout window (stops slow guessing)."""
    settings = get_settings()
    since = clock.now() - timedelta(hours=settings.login_lockout_hours)
    return _failures_since(session, email, since) >= settings.login_max_failures_per_day


def send_code(session: Session, email: str) -> None:
    """Email a sign-in code, if the account exists (or sign-up is open) and no limit is reached.

    Runs in the worker (identity.tasks), never inside the web request: the request only
    puts a job on the queue, so its timing is the same whether or not the account exists.
    """
    settings = get_settings()
    email = normalise_email(email)
    now = clock.now()

    known = session.scalar(select(User.id).where(User.email == email)) is not None
    if not known and not settings.signup_is_open:
        return

    def codes_since(since: datetime) -> int:
        return session.scalar(
            select(func.count())
            .select_from(LoginCode)
            .where(LoginCode.email == email, LoginCode.created_at > since)
        ) or 0

    if codes_since(now - timedelta(minutes=settings.login_code_minutes)) >= (
        settings.login_code_max_requests
    ):
        return
    day_start = now - timedelta(hours=settings.login_lockout_hours)
    if codes_since(day_start) >= settings.login_max_codes_per_day:
        log.info("daily limit of sign-in codes reached for one address")
        return
    if is_locked_out(session, email):
        log.info("sign-in codes paused for one address after too many wrong codes")
        return

    code = security.new_login_code()
    session.add(
        LoginCode(
            email=email,
            code_hash=security.hash_login_code(email, code),
            created_at=now,
            expires_at=now + timedelta(minutes=settings.login_code_minutes),
        )
    )
    session.flush()
    try:
        get_mailer().send(
            to=email,
            subject=f"Your AI-LMS sign-in code: {code}",
            text=(
                f"Your sign-in code is {code}\n\n"
                f"It works once and expires in {settings.login_code_minutes} minutes.\n"
                "If you did not ask for it, you can ignore this email.\n"
            ),
        )
    except OSError:
        # The operator sees it in the log; the person can ask for a new code.
        log.exception("could not send the sign-in email")


def verify_code(session: Session, raw_email: str, code: str) -> User:
    """Check a code and return the user, creating a student account if sign-up is open."""
    settings = get_settings()
    try:
        email = normalise_email(raw_email)
    except ValueError as error:
        raise SignInError from error
    now = clock.now()

    login_code = session.scalar(
        select(LoginCode)
        .where(
            LoginCode.email == email,
            LoginCode.consumed_at.is_(None),
            LoginCode.expires_at > now,
        )
        .order_by(LoginCode.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    if login_code is None or login_code.attempts >= settings.login_code_max_attempts:
        raise SignInError
    # Even the right code is refused while the address is locked out.
    if is_locked_out(session, email):
        raise SignInError
    if not security.same(login_code.code_hash, security.hash_login_code(email, code.strip())):
        login_code.attempts += 1
        raise SignInError
    login_code.consumed_at = now

    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        if not settings.signup_is_open:
            raise SignInError
        user = User(email=email, display_name=email.split("@")[0], role=Role.STUDENT.value)
        session.add(user)
        session.flush()
    return user


# --- demo entry (ADR 0008 section G) ----------------------------------------


def demo_user(session: Session, role: Role, access_code: str | None) -> User | None:
    """The demo account for a role. The caller has already checked that demo mode is on."""
    settings = get_settings()
    if settings.access_code_required and not security.same(
        access_code or "", settings.demo_access_code
    ):
        raise AccessCodeError
    return session.scalar(
        select(User)
        .where(User.is_demo.is_(True), User.role == role.value)
        .order_by(User.created_at)
        .limit(1)
    )


# --- sessions ---------------------------------------------------------------


def start_session(session: Session, user: User) -> str:
    """Create a session row and return the token that goes into the cookie."""
    token = security.new_session_token()
    now = clock.now()
    session.add(
        UserSession(
            user_id=user.id,
            token_hash=security.hash_token(token),
            created_at=now,
            expires_at=now + timedelta(days=get_settings().session_days),
        )
    )
    session.flush()
    return token


def find_session_user(session: Session, token: str) -> CurrentUser | None:
    """Who a cookie belongs to. Runs before the organisation is known, so unfiltered."""
    with system_scope(session):
        row = session.execute(
            select(User, Organisation)
            .join(UserSession, UserSession.user_id == User.id)
            .join(Organisation, Organisation.id == User.organisation_id)
            .where(
                UserSession.token_hash == security.hash_token(token),
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > clock.now(),
            )
        ).first()
    if row is None:
        return None
    return _to_current(row[0], row[1])


def end_session(session: Session, token: str) -> None:
    with system_scope(session):
        found = session.scalar(
            select(UserSession).where(UserSession.token_hash == security.hash_token(token))
        )
        if found is not None and found.revoked_at is None:
            found.revoked_at = clock.now()
            session.flush()

