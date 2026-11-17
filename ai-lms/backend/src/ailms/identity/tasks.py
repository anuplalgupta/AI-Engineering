"""Identity jobs run by the worker."""

import uuid

from ailms.identity import service
from ailms.platform.db import scope_to_organisation, session_scope
from ailms.platform.queue import app


@app.task(name="identity.send_sign_in_code", queue="default")
def send_sign_in_code(organisation_id: str, email: str) -> None:
    """Decide whether to send a sign-in code, and send it. See service.send_code."""
    with session_scope() as session:
        scope_to_organisation(session, uuid.UUID(organisation_id))
        service.send_code(session, email)
