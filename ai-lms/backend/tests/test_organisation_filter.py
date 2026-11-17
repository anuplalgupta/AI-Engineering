"""The organisation filter (ADR 0001 item 6): one shared layer, tested with two organisations."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import column, delete, func, insert, select, table, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError

from ailms.catalog import service as catalog_service
from ailms.catalog.models import Course, Programme, Topic, TopicPrerequisite
from ailms.catalog.service import list_prerequisites, list_topics
from ailms.content import service as content_service
from ailms.content.models import Lesson, LessonVersion
from ailms.identity import service as identity_service
from ailms.identity.api import Role
from ailms.identity.models import LoginCode, User, UserSession
from ailms.platform.audit import StatusChange
from ailms.platform.db import (
    OrganisationOwned,
    get_admin_engine,
    get_engine,
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
        user_id = identity_service.ensure_user(
            session, email="student@demo.example", display_name="x", role=Role.STUDENT
        )
        assert session.get(User, user_id).organisation_id == orgs.a


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


# --- raw SQL fails closed in the ORM layer ---------------------------------------------


def test_raw_sql_is_refused_in_a_scoped_session(orgs):
    with session_scope() as session:
        scope_to_organisation(session, orgs.a)
        with pytest.raises(UnscopedQueryError):
            session.execute(text("select id from lesson"))
        with pytest.raises(UnscopedQueryError):
            session.execute(select(table("lesson", column("id"))))
        with pytest.raises(UnscopedQueryError):
            session.execute(select(Topic).where(text("true")))


def test_raw_sql_is_refused_in_an_unscoped_session(orgs):
    with session_scope() as session:
        with pytest.raises(UnscopedQueryError):
            session.execute(text("select 1"))


def test_raw_sql_is_allowed_inside_system_scope(orgs):
    with session_scope() as session, system_scope(session):
        rows = session.execute(text("select organisation_id from lesson")).all()
    assert {row[0] for row in rows} == {orgs.a, orgs.b}


# --- row-level security: the database's own copy of the filter -------------------------


def _lesson_orgs_via_connection(session) -> set:
    # session.connection().execute skips the ORM event; only the database policy applies.
    return {row[0] for row in session.connection().execute(text("select organisation_id from lesson"))}


def test_sql_that_bypasses_the_orm_sees_own_organisation_only(orgs):
    with session_scope() as session:
        scope_to_organisation(session, orgs.a)
        assert _lesson_orgs_via_connection(session) == {orgs.a}
    with session_scope() as session:
        scope_to_organisation(session, uuid.uuid4())  # an organisation with no data
        assert _lesson_orgs_via_connection(session) == set()


def test_sql_that_bypasses_the_orm_sees_nothing_when_unscoped(orgs):
    with session_scope() as session:
        assert _lesson_orgs_via_connection(session) == set()
    with get_engine().connect() as connection:
        assert connection.execute(text("select count(*) from lesson")).scalar() == 0


def test_scope_set_after_the_transaction_started_reaches_the_database(orgs):
    with session_scope() as session:
        assert _lesson_orgs_via_connection(session) == set()
        scope_to_organisation(session, orgs.b)
        assert _lesson_orgs_via_connection(session) == {orgs.b}
        with system_scope(session):
            assert _lesson_orgs_via_connection(session) == {orgs.a, orgs.b}
        assert _lesson_orgs_via_connection(session) == {orgs.b}


def test_database_refuses_writing_another_organisations_row(orgs):
    with session_scope() as session:
        scope_to_organisation(session, orgs.a)
        with pytest.raises(DBAPIError):
            session.connection().execute(
                text("insert into programme (id, title, created_at, organisation_id) "
                     "values (:id, 'x', now(), :org)"),
                {"id": uuid.uuid4(), "org": orgs.b},
            )


def test_application_role_has_no_superuser_rights():
    with get_engine().connect() as connection:
        row = connection.execute(
            text("select rolsuper, rolbypassrls, rolcreatedb, rolcreaterole from pg_roles "
                 "where rolname = current_user")
        ).one()
    assert tuple(row) == (False, False, False, False)


def test_every_organisation_owned_table_has_row_level_security():
    names = sorted(t.name for t in organisation_owned_tables())
    with get_admin_engine().connect() as connection:
        enabled = dict(
            connection.execute(
                text("select relname, relrowsecurity from pg_class where relname = any(:names)"),
                {"names": names},
            ).all()
        )
        policies = set(
            connection.execute(
                text("select tablename from pg_policies where policyname = 'organisation_isolation'")
            ).scalars()
        )
    assert enabled == dict.fromkeys(names, True)
    assert set(names) <= policies


# --- links between rows stay inside one organisation -----------------------------------


def _one(model, organisation_id, *where):
    with session_scope() as session, system_scope(session):
        return session.scalars(
            select(model).where(model.organisation_id == organisation_id, *where)
        ).first()


def test_database_refuses_a_lesson_on_another_organisations_topic(orgs):
    b_topic = _one(Topic, orgs.b)
    with pytest.raises(IntegrityError), session_scope() as session:
        scope_to_organisation(session, orgs.a)
        session.add(Lesson(topic_id=b_topic.id, format="tutorial"))
        session.flush()


def test_database_refuses_a_prerequisite_in_another_organisation(orgs):
    a_topic = _one(Topic, orgs.a)
    b_topic = _one(Topic, orgs.b)
    with pytest.raises(IntegrityError), session_scope() as session:
        scope_to_organisation(session, orgs.a)
        session.add(TopicPrerequisite(topic_id=a_topic.id, prerequisite_id=b_topic.id))
        session.flush()


def test_database_refuses_a_session_for_another_organisations_user(orgs):
    b_user = _one(User, orgs.b)
    with pytest.raises(IntegrityError), session_scope() as session:
        scope_to_organisation(session, orgs.a)
        session.add(UserSession(user_id=b_user.id, token_hash="x" * 64,
                                expires_at=datetime(2030, 1, 1, tzinfo=UTC)))
        session.flush()


def test_published_version_must_belong_to_the_same_lesson(orgs):
    a_lesson = _one(Lesson, orgs.a)
    a_topic = _one(Topic, orgs.a, Topic.id != a_lesson.topic_id)
    with pytest.raises(IntegrityError), session_scope() as session:
        scope_to_organisation(session, orgs.a)
        other = Lesson(topic_id=a_topic.id, format="tutorial")
        session.add(other)
        session.flush()
        # Point the new lesson at the sample lesson's version.
        other.published_version_id = a_lesson.published_version_id
        session.flush()
