import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKeyConstraint, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ailms.platform import clock
from ailms.platform.db import Base, OrganisationOwned, new_id


class Organisation(Base):
    """The operator of one deployment. The pilot has exactly one."""

    __tablename__ = "organisation"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(default=clock.now)


class User(OrganisationOwned, Base):
    __tablename__ = "user_account"
    __table_args__ = (
        UniqueConstraint("organisation_id", "email"),
        UniqueConstraint("id", "organisation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(254))
    display_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=clock.now)


class UserSession(OrganisationOwned, Base):
    __tablename__ = "user_session"
    __table_args__ = (
        # The user belongs to the same organisation as the session.
        ForeignKeyConstraint(
            ["user_id", "organisation_id"],
            ["user_account.id", "user_account.organisation_id"],
            ondelete="CASCADE",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(default=clock.now)
    expires_at: Mapped[datetime] = mapped_column()
    revoked_at: Mapped[datetime | None] = mapped_column()


class LoginCode(OrganisationOwned, Base):
    """A one-time sign-in code. Only its keyed hash is stored."""

    __tablename__ = "login_code"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(254), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(default=clock.now)
    expires_at: Mapped[datetime] = mapped_column()
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    consumed_at: Mapped[datetime | None] = mapped_column()
