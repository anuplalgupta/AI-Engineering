import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ailms.platform import clock
from ailms.platform.db import Base, OrganisationOwned, new_id


class Programme(OrganisationOwned, Base):
    """What a student prepares for, for example an entrance examination."""

    __tablename__ = "programme"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(default=clock.now)


class Course(OrganisationOwned, Base):
    __tablename__ = "course"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    programme_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("programme.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(300))
    subject: Mapped[str] = mapped_column(String(100))
    level: Mapped[str] = mapped_column(String(100))
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=clock.now)


class Topic(OrganisationOwned, Base):
    __tablename__ = "topic"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("course.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("topic.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(300))
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=clock.now)


class TopicPrerequisite(OrganisationOwned, Base):
    """topic_id needs prerequisite_id first."""

    __tablename__ = "topic_prerequisite"

    topic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("topic.id", ondelete="CASCADE"), primary_key=True
    )
    prerequisite_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("topic.id", ondelete="CASCADE"), primary_key=True, index=True
    )
