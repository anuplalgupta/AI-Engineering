"""The organisation filter (ADR 0001 item 6): one shared layer, tested with two organisations."""

import uuid

import pytest
from sqlalchemy import delete, func, insert, select, update

from ailms.catalog.api import Course, Programme, Topic, TopicPrerequisite, list_prerequisites, list_topics
from ailms.catalog import service as catalog_service
from ailms.content import service as content_service
from ailms.content.api import Lesson, LessonVersion
from ailms.identity import service as identity_service
from ailms.identity.api import LoginCode, Role, User, UserSession
from ailms.platform.audit import StatusChange
from ailms.platform.db import (
    OrganisationOwned,
    UnscopedQueryError,
    organisation_owned_tables,
    scope_to_organisation,
    session_scope,
    system_scope,
)

OWNED = [Programme, Course, Topic, TopicPrerequisite, Lesson, LessonVersion, User, UserSession,
         LoginCode, StatusChange]


def test_every_data_table_is_organisation_owned():
    names = {table.name for table in organisation_owned_tables()}
    assert names == {model.__tablename__ for model in OWNED}
    for table in organisation_owned_tables():
        column = table.c.organisation_id
        assert not column.nullable
        assert any(fk.column.table.name == "organisation" for fk in column.foreign_keys)


@pytest.mark.parametrize("model", OWNED, ids=lambda m: m.__tablename__)
def test_unscoped_query_raises(orgs, model):
    with session_scope() as session, pytest.raises(UnscopedQueryError):
        session.execute(select(model))


def test_unscoped_count_and_get_raise(orgs):
    with session_scope() as session:
        with pytest.raises(UnscopedQueryError):
            session.scalar(select(func.count()).select_from(Topic))
        with pytest.raises(UnscopedQueryError):
            session.get(Course, uuid.uuid4())


def test_unscoped_insert_raises(orgs):
    with pytest.raises(UnscopedQueryError), session_scope() as session:
        session.add(Programme(title="Nobody's programme"))
        session.flush()


def test_core_insert_on_owned_table_is_refused(orgs):
    with session_scope() as session:
        scope_to_organisation(session, orgs.a)
        with pytest.raises(UnscopedQueryError):
            session.execute(insert(Programme).values(id=uuid.uuid4(), title="x", organisation_id=orgs.b))


@pytest.mark.parametrize("model", OWNED, ids=lambda m: m.__tablename__)
def test_scoped_query_sees_own_organisation_only(orgs, model):
    for mine, theirs in ((orgs.a, orgs.b), (orgs.b, orgs.a)):
        with session_scope() as session:
            scope_to_organisation(session, mine)
            rows = list(session.scalars(select(model)))
            assert all(row.organisation_id == mine for row in rows)
            if model not in (UserSession, LoginCode):  # none of these exist yet
                assert rows, model


def test_twin_rows_exist_in_both(orgs):
    with session_scope() as session, system_scope(session):
        per_org = dict(
            session.execute(select(Topic.organisation_id, func.count()).group_by(Topic.organisation_id)).all()
        )
    assert per_org[orgs.a] == per_org[orgs.b] > 0


def test_get_by_id_of_other_organisation_returns_nothing(orgs):
    with session_scope() as session, system_scope(session):
        other_course = session.scalars(select(Course).where(Course.organisation_id == orgs.b)).one()
        other_lesson = session.scalars(select(Lesson).where(Lesson.organisation_id == orgs.b)).one()
    with session_scope() as session:
        scope_to_organisation(session, orgs.a)
        assert session.get(Course, other_course.id) is None
        assert catalog_service.get_course(session, other_course.id) is None
        assert list_topics(session, other_course.id) == []
        assert list_prerequisites(session, other_course.id) == []
        assert content_service.get_lesson_for_reading(session, other_lesson.id, staff=True) is None


def test_repository_functions_do_not_leak(orgs):
    with session_scope() as session, system_scope(session):
        b_topics = [t.id for t in session.scalars(select(Topic).where(Topic.organisation_id == orgs.b))]
    with session_scope() as session:
        scope_to_organisation(session, orgs.a)
        courses = catalog_service.list_courses(session)
        assert courses and all(c.organisation_id == orgs.a and p.organisation_id == orgs.a for c, p in courses)
        assert content_service.published_lesson_summaries(session, b_topics) == {}
        assert identity_service.demo_user(session, Role.STUDENT, None).organisation_id == orgs.a
        user = identity_service.ensure_user(
            session, email="student@demo.example", display_name="x", role=Role.STUDENT
        )
        assert user.organisation_id == orgs.a


def test_bulk_update_and_delete_are_filtered(orgs):
    with session_scope() as session:
        scope_to_organisation(session, orgs.a)
        session.execute(update(Topic).values(title="Renamed"))
        session.execute(delete(TopicPrerequisite))
    with session_scope() as session, system_scope(session):
        titles_b = set(session.scalars(select(Topic.title).where(Topic.organisation_id == orgs.b)))
        links_b = session.scalar(
            select(func.count()).select_from(TopicPrerequisite).where(TopicPrerequisite.organisation_id == orgs.b)
        )
    assert "Renamed" not in titles_b
    assert links_b > 0


def test_insert_gets_organisation_automatically(orgs):
    with session_scope() as session:
        scope_to_organisation(session, orgs.b)
        programme = Programme(title="Added")
        session.add(programme)
        session.flush()
        assert programme.organisation_id == orgs.b


def test_cannot_save_row_for_another_organisation(orgs):
    with pytest.raises(UnscopedQueryError), session_scope() as session:
        scope_to_organisation(session, orgs.a)
        session.add(Programme(title="Smuggled", organisation_id=orgs.b))
        session.flush()


def test_session_cannot_switch_organisation(orgs):
    with session_scope() as session:
        scope_to_organisation(session, orgs.a)
        with pytest.raises(UnscopedQueryError):
            scope_to_organisation(session, orgs.b)


def test_mixin_is_on_every_owned_model():
    for model in OWNED:
        assert issubclass(model, OrganisationOwned)
