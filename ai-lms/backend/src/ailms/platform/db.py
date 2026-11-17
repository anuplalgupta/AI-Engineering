"""Database engine, base classes and the organisation filter (ADR 0001 item 6).

Every table with operator or student data inherits OrganisationOwned. A session
must be given an organisation with scope_to_organisation() before it touches
such a table:

* reads, updates and deletes are filtered to that organisation automatically;
* new rows get the organisation set automatically;
* with no organisation set, the statement is refused (UnscopedQueryError).

system_scope() is the one explicit way round the filter, for start-up tasks and
for finding a session row from its cookie before the organisation is known.
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from functools import lru_cache
from typing import Any

from sqlalchemy import DateTime, Engine, ForeignKey, MetaData, Table, Uuid, create_engine, event
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    ORMExecuteState,
    Session,
    declared_attr,
    mapped_column,
    sessionmaker,
    with_loader_criteria,
)
from sqlalchemy.sql import visitors

from ailms.platform.settings import get_settings

_ORG_KEY = "organisation_id"
_SYSTEM_KEY = "system_scope"

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class UnscopedQueryError(RuntimeError):
    """An organisation-owned table was used with no organisation set."""


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {datetime: DateTime(timezone=True), uuid.UUID: Uuid}


def new_id() -> uuid.UUID:
    return uuid.uuid4()


class OrganisationOwned:
    """Mixin for every table that holds an organisation's data."""

    @declared_attr
    def organisation_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            ForeignKey("organisation.id", ondelete="RESTRICT"), index=True, nullable=False
        )


def organisation_owned_tables() -> set[Table]:
    return {
        mapper.local_table  # type: ignore[misc]
        for mapper in Base.registry.mappers
        if issubclass(mapper.class_, OrganisationOwned)
    }


def _tables_in(statement: Any) -> set[Table]:
    return {el for el in visitors.iterate(statement) if isinstance(el, Table)}


def scope_to_organisation(session: Session, organisation_id: uuid.UUID) -> None:
    current = session.info.get(_ORG_KEY)
    if current is not None and current != organisation_id:
        raise UnscopedQueryError("this session already belongs to another organisation")
    session.info[_ORG_KEY] = organisation_id


def current_organisation_id(session: Session) -> uuid.UUID:
    organisation_id = session.info.get(_ORG_KEY)
    if organisation_id is None:
        raise UnscopedQueryError("no organisation is set for this session")
    return organisation_id


@contextmanager
def system_scope(session: Session) -> Iterator[None]:
    """Switch the filter off for the enclosed block. Use sparingly."""
    previous = session.info.get(_SYSTEM_KEY, False)
    session.info[_SYSTEM_KEY] = True
    try:
        yield
    finally:
        session.info[_SYSTEM_KEY] = previous


@event.listens_for(Session, "do_orm_execute")
def _apply_organisation_filter(state: ORMExecuteState) -> None:
    if state.session.info.get(_SYSTEM_KEY):
        return
    touched = _tables_in(state.statement) & organisation_owned_tables()
    if not touched:
        return
    names = ", ".join(sorted(t.name for t in touched))
    organisation_id = state.session.info.get(_ORG_KEY)
    if organisation_id is None:
        raise UnscopedQueryError(f"query on {names} with no organisation set")
    filterable = (state.is_select or state.is_update or state.is_delete) and state.is_orm_statement
    if not filterable:
        # Plain inserts and table-level statements cannot be filtered automatically.
        raise UnscopedQueryError(
            f"statement on {names} must use mapped classes so that it can be filtered"
        )
    if state.is_column_load or state.is_relationship_load:
        # The criteria travel with the statement that loaded the parent row.
        return
    state.statement = state.statement.options(
        with_loader_criteria(
            OrganisationOwned,
            lambda cls: cls.organisation_id == organisation_id,
            include_aliases=True,
        )
    )


@event.listens_for(Session, "before_flush")
def _stamp_organisation(session: Session, flush_context: Any, instances: Any) -> None:
    system = session.info.get(_SYSTEM_KEY, False)
    organisation_id = session.info.get(_ORG_KEY)
    for obj in list(session.new) + list(session.dirty) + list(session.deleted):
        if not isinstance(obj, OrganisationOwned):
            continue
        if obj.organisation_id is None:
            if organisation_id is None:
                raise UnscopedQueryError(
                    f"cannot save {type(obj).__name__} with no organisation set"
                )
            obj.organisation_id = organisation_id
        elif not system and obj.organisation_id != organisation_id:
            raise UnscopedQueryError(
                f"cannot save {type(obj).__name__} for a different organisation"
            )


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def new_session() -> Session:
    return _session_factory()()


@contextmanager
def session_scope() -> Iterator[Session]:
    """A session that commits on success and rolls back on error."""
    session = new_session()
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    with session_scope() as session:
        yield session
