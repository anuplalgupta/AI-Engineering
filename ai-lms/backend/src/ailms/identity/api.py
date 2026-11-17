"""Public interface of the identity module. Other modules import from here only.

Only service functions, dependencies and plain data types are exported, never the
tables (ORM classes): sessions and sign-in codes are handled by identity alone.
"""

from ailms.identity.deps import SESSION_COOKIE, current_user, organisation_session, require_role
from ailms.identity.routes import ErrorOut, router
from ailms.identity.service import (
    CurrentUser,
    Role,
    any_organisation_exists,
    ensure_organisation,
    ensure_user,
    organisation_id_by_slug,
)

__all__ = [
    "SESSION_COOKIE",
    "CurrentUser",
    "ErrorOut",
    "Role",
    "any_organisation_exists",
    "current_user",
    "ensure_organisation",
    "ensure_user",
    "organisation_id_by_slug",
    "organisation_session",
    "require_role",
    "router",
]
