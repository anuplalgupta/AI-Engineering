"""The status-change log (ADR 0001 item 5): who moved which item from what to what, and when."""

import uuid
from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from ailms.platform import clock
from ailms.platform.db import Base, OrganisationOwned, new_id


class StatusChange(OrganisationOwned, Base):
    __tablename__ = "status_change"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    item_kind: Mapped[str] = mapped_column(String(40), index=True)
    item_id: Mapped[uuid.UUID] = mapped_column(index=True)
    old_status: Mapped[str | None] = mapped_column(String(40))
    new_status: Mapped[str] = mapped_column(String(40))
    # "user", "worker" or "system"; actor_id is the user when a person made the change.
    actor_kind: Mapped[str] = mapped_column(String(20))
    actor_id: Mapped[uuid.UUID | None] = mapped_column()
    changed_at: Mapped[datetime] = mapped_column(default=clock.now)
    comment: Mapped[str | None] = mapped_column(Text)


def record_status_change(
    session: Session,
    *,
    item_kind: str,
    item_id: uuid.UUID,
    old_status: str | None,
    new_status: str,
    actor_kind: str = "system",
    actor_id: uuid.UUID | None = None,
    comment: str | None = None,
) -> StatusChange:
    change = StatusChange(
        item_kind=item_kind,
        item_id=item_id,
        old_status=old_status,
        new_status=new_status,
        actor_kind=actor_kind,
        actor_id=actor_id,
        comment=comment,
    )
    session.add(change)
    return change
