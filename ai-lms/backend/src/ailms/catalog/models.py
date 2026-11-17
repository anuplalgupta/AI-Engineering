import uuid
from datetime import datetime

from sqlalchemy import ForeignKeyConstraint, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ailms.platform import clock
from ailms.platform.db import Base, OrganisationOwned, new_id

# Every link between two organisation-owned rows includes organisation_id, so the
# database itself refuses a link to another organisation's row.


def _same_organisation(columns: str, table: str) -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        [columns, "organisation_id"], [f"{table}.id", f"{table}.organisation_id"],
        ondelete="CASCADE",
    )


class Programme(OrganisationOwned, Base):
    """What a student prepares for, for example an entrance examination."""

    __tablename__ = "programme"
    __table_args__ = (UniqueConstraint("id", "organisation_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(default=clock.now)


class Course(OrganisationOwned, Base):
    __tablename__ = "course"
    __table_args__ = (
        UniqueConstraint("id", "organisation_id"),
        _same_organisation("programme_id", "programme"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    programme_id: Mapped[uuid.UUID] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(String(300))
    subject: Mapped[str] = mapped_column(String(100))
    level: Mapped[str] = mapped_column(String(100))
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=clock.now)


class Topic(OrganisationOwned, Base):
    __tablename__ = "topic"
    __table_args__ = (
        UniqueConstraint("id", "organisation_id"),
        _same_organisation("course_id", "course"),
        _same_organisation("parent_id", "topic"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    course_id: Mapped[uuid.UUID] = mapped_column(index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(String(300))
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=clock.now)


class TopicPrerequisite(OrganisationOwned, Base):
    """topic_id needs prerequisite_id first."""

    __tablename__ = "topic_prerequisite"
    __table_args__ = (
        _same_organisation("topic_id", "topic"),
        _same_organisation("prerequisite_id", "topic"),
    )

    topic_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    prerequisite_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, index=True)
