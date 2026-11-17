"""Counting requests per client address, kept in the database so every container shares it.

Only a keyed hash of the address is stored, and rows older than the window are removed.
"""

import hashlib
import hmac
import uuid
from datetime import datetime, timedelta

from sqlalchemy import Index, String, delete, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from ailms.platform import clock
from ailms.platform.db import Base, new_id
from ailms.platform.settings import get_settings


class ClientRateEvent(Base):
    """One counted request from one client address. Holds no organisation data."""

    __tablename__ = "client_rate_event"
    __table_args__ = (Index(None, "action", "client_hash", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    action: Mapped[str] = mapped_column(String(40))
    client_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column()


def _client_hash(client: str) -> str:
    key = get_settings().secret_key.encode()
    return hmac.new(key, f"client\n{client}".encode(), hashlib.sha256).hexdigest()


def allow(session: Session, *, action: str, client: str, limit: int, window: timedelta) -> bool:
    """Count one request; False when the client already made `limit` of them in the window."""
    now = clock.now()
    key = _client_hash(client)
    session.execute(
        delete(ClientRateEvent).where(
            ClientRateEvent.action == action,
            ClientRateEvent.client_hash == key,
            ClientRateEvent.created_at <= now - window,
        )
    )
    used = session.scalar(
        select(func.count())
        .select_from(ClientRateEvent)
        .where(ClientRateEvent.action == action, ClientRateEvent.client_hash == key)
    )
    if (used or 0) >= limit:
        return False
    session.add(ClientRateEvent(action=action, client_hash=key, created_at=now))
    session.flush()
    return True
