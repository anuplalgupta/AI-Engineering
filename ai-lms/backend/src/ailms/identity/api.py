"""Public interface of the identity module. Other modules import from here only."""

from ailms.identity.deps import SESSION_COOKIE, current_user, organisation_session, require_role
from ailms.identity.models import LoginCode, Organisation, User, UserSession
from ailms.identity.routes import ErrorOut, router
from ailms.identity.service import (
    CurrentUser,
    Role,
    any_organisation_exists,
    ensure_organisation,
    ensure_user,
    organisation_by_slug,
    start_session,
)

__all__ = [
    "SESSION_COOKIE",
    "CurrentUser",
    "ErrorOut",
    "LoginCode",
    "Organisation",
    "Role",
    "User",
    "UserSession",
    "any_organisation_exists",
    "current_user",
    "ensure_organisation",
    "ensure_user",
    "organisation_by_slug",
    "organisation_session",
    "require_role",
    "router",
    "start_session",
]
