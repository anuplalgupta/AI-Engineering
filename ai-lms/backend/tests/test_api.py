"""The API contract, published-only lessons, media, and isolation between organisations."""

import uuid

import pytest
from sqlalchemy import select

from ailms import __version__
from ailms.catalog.models import Topic
from ailms.content.api import VersionStatus, import_tutorial
from ailms.content.models import Lesson, LessonVersion
from ailms.content.service import add_version, set_version_status, withdraw_lesson
from ailms.platform.db import scope_to_organisation, session_scope, system_scope
from ailms.platform.storage import organisation_key
from conftest import demo_login, sign_in_as


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok", "version": __version__}


def test_config_local_demo(client):
    assert client.get("/api/config").json() == {
        "demo_mode": True,
        "signup_open": True,
        "access_code_required": False,
        "banner": None,
    }


def test_openapi_is_served(client):
    document = client.get("/api/openapi.json").json()
    assert document["info"]["title"] == "AI-LMS API"
    for path in ("/api/health", "/api/config", "/api/auth/request-code", "/api/auth/verify-code",
                 "/api/auth/demo-login", "/api/auth/logout", "/api/me", "/api/courses",
                 "/api/courses/{course_id}/topics", "/api/lessons/{lesson_id}", "/api/media/{key}"):
        assert path in document["paths"], path


@pytest.mark.parametrize(
    "path", ["/api/courses", f"/api/courses/{uuid.uuid4()}/topics", f"/api/lessons/{uuid.uuid4()}",
             "/api/media/sample/vectors/vector-components.svg"],
)
def test_signed_in_routes_need_a_session(client, orgs, path):
    response = client.get(path)
    assert response.status_code == 401
    assert response.json() == {"detail": "Please sign in."}


def test_courses_and_topics(client, orgs):
    demo_login(client, "student")
    courses = client.get("/api/courses").json()
    assert len(courses) == 1
    course = courses[0]
    assert course["title"] == "Physics, Class 11 (sample): Vectors and Kinematics"
    assert course["programme"]["title"] == "JEE Main (sample)"
    assert set(course) == {"id", "title", "subject", "level", "programme"}

    topics = client.get(f"/api/courses/{course['id']}/topics").json()
    assert 8 <= len(topics) <= 14
    ids = {t["id"] for t in topics}
    assert all(t["parent_id"] is None or t["parent_id"] in ids for t in topics)
    with_lesson = [t for t in topics if t["lesson"]]
    assert len(with_lesson) == 1
    lesson = with_lesson[0]["lesson"]
    assert lesson["format"] == "tutorial" and lesson["estimated_minutes"] > 0
    assert set(with_lesson[0]) == {"id", "parent_id", "title", "position", "lesson"}


def test_unknown_course_is_404(client, orgs):
    demo_login(client, "student")
    assert client.get(f"/api/courses/{uuid.uuid4()}/topics").status_code == 404


def _published_lesson_id(client) -> str:
    course = client.get("/api/courses").json()[0]
    topics = client.get(f"/api/courses/{course['id']}/topics").json()
    return next(t["lesson"]["id"] for t in topics if t["lesson"])


def test_lesson_document(client, orgs):
    demo_login(client, "student")
    lesson = client.get(f"/api/lessons/{_published_lesson_id(client)}").json()
    assert lesson["format"] == "tutorial" and lesson["version"] == 1
    assert "CC BY 4.0" in lesson["attribution"]
    document = lesson["document"]
    assert document["schema_version"] == 1
    types = [s["type"] for s in document["sections"]]
    for needed in ("explanation", "derivation", "worked_example", "diagram", "key_points", "summary"):
        assert needed in types
    diagram = next(s for s in document["sections"] if s["type"] == "diagram")
    assert client.get(f"/api/media/{diagram['image']['key']}").status_code == 200


def _add_draft_lesson(organisation_id: uuid.UUID) -> uuid.UUID:
    lesson_id = uuid.uuid4()
    with session_scope() as session:
        scope_to_organisation(session, organisation_id)
        topic = session.scalars(select(Topic).where(Topic.title == "Free fall")).one()
        import_tutorial(
            session, lesson_id=lesson_id, version_id=uuid.uuid4(), topic_id=topic.id,
            title="Draft on free fall", estimated_minutes=5, attribution=None, publish=False,
            document={"schema_version": 1, "sections": [
                {"id": "s1", "type": "summary", "body_md": "Draft.", "sources": []}]},
        )
    return lesson_id


def test_students_never_get_unpublished_lessons(client, orgs):
    draft_id = _add_draft_lesson(orgs.a)
    demo_login(client, "student")
    assert client.get(f"/api/lessons/{draft_id}").status_code == 404
    course = client.get("/api/courses").json()[0]
    topics = client.get(f"/api/courses/{course['id']}/topics").json()
    assert all(t["lesson"] is None or t["lesson"]["id"] != str(draft_id) for t in topics)
    # Staff may open the draft by its id.
    demo_login(client, "reviewer")
    assert client.get(f"/api/lessons/{draft_id}").status_code == 200


def test_withdrawn_lesson_hidden_from_students(client, orgs):
    demo_login(client, "student")
    lesson_id = _published_lesson_id(client)
    with session_scope() as session:
        scope_to_organisation(session, orgs.a)
        withdraw_lesson(session, uuid.UUID(lesson_id), comment="Out of date")
    assert client.get(f"/api/lessons/{lesson_id}").status_code == 404
    course = client.get("/api/courses").json()[0]
    topics = client.get(f"/api/courses/{course['id']}/topics").json()
    assert all(t["lesson"] is None for t in topics)


def _second_version(organisation_id: uuid.UUID, lesson_id: str) -> uuid.UUID:
    with session_scope() as session:
        scope_to_organisation(session, organisation_id)
        return add_version(
            session, lesson_id=uuid.UUID(lesson_id), title="Edited title", estimated_minutes=7,
            attribution=None, comment="Edit",
            document={"schema_version": 1, "sections": [
                {"id": "s1", "type": "summary", "body_md": "Edited.", "sources": []}]},
        )


@pytest.mark.parametrize(
    "status", [s for s in VersionStatus if s is not VersionStatus.PUBLISHED], ids=str
)
def test_students_keep_the_published_version_while_an_edit_is_reviewed(client, orgs, status):
    demo_login(client, "student")
    lesson_id = _published_lesson_id(client)
    original = client.get(f"/api/lessons/{lesson_id}").json()
    version_id = _second_version(orgs.a, lesson_id)
    with session_scope() as session:
        scope_to_organisation(session, orgs.a)
        if status is not VersionStatus.DRAFT:
            set_version_status(session, version_id, status)
    # The student still gets version 1; staff see the edit in review.
    assert client.get(f"/api/lessons/{lesson_id}").json() == original
    course = client.get("/api/courses").json()[0]
    topics = client.get(f"/api/courses/{course['id']}/topics").json()
    assert any(t["lesson"] and t["lesson"]["id"] == lesson_id for t in topics)
    demo_login(client, "reviewer")
    staff_view = client.get(f"/api/lessons/{lesson_id}").json()
    assert staff_view["version"] == 2 and staff_view["title"] == "Edited title"


def test_publishing_an_edit_replaces_the_version_students_see(client, orgs):
    demo_login(client, "student")
    lesson_id = _published_lesson_id(client)
    version_id = _second_version(orgs.a, lesson_id)
    with session_scope() as session:
        scope_to_organisation(session, orgs.a)
        set_version_status(session, version_id, VersionStatus.IN_REVIEW)
        set_version_status(session, version_id, VersionStatus.PUBLISHED)
    lesson = client.get(f"/api/lessons/{lesson_id}").json()
    assert lesson["version"] == 2 and lesson["title"] == "Edited title"
    # Each version's status changes are logged against that version.
    from ailms.platform.audit import StatusChange

    with session_scope() as session:
        scope_to_organisation(session, orgs.a)
        changes = session.scalars(
            select(StatusChange).where(StatusChange.item_id == version_id)
            .order_by(StatusChange.changed_at, StatusChange.new_status)
        ).all()
        assert {c.item_kind for c in changes} == {"lesson_version"}
        assert [c.new_status for c in changes] == ["draft", "in_review", "published"]
        versions = session.scalars(
            select(LessonVersion).where(LessonVersion.lesson_id == uuid.UUID(lesson_id))
        ).all()
        assert sorted(v.status for v in versions) == ["published", "published"]


def test_media_headers_keep_svg_scripts_from_running(client, orgs):
    demo_login(client, "student")
    response = client.get("/api/media/sample/vectors/vector-components.svg")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    csp = response.headers["content-security-policy"]
    assert "sandbox" in csp and "default-src 'none'" in csp
    assert response.headers["x-content-type-options"] == "nosniff"
    assert b"<script" not in response.content


def test_media_rejects_bad_keys(client, orgs):
    demo_login(client, "student")
    for key in ("../etc/passwd", "sample/../../x", "missing/file.svg"):
        assert client.get(f"/api/media/{key}").status_code == 404


# --- two organisations: no route leaks ------------------------------------------


def test_routes_do_not_leak_across_organisations(client, orgs, store):
    with session_scope() as session, system_scope(session):
        b_lesson = session.scalars(select(Lesson).where(Lesson.organisation_id == orgs.b)).one()
        b_topic = session.get(Topic, b_lesson.topic_id)
    store.put(organisation_key(orgs.b, "private/only-b.png"), b"\x89PNG", "image/png")

    sign_in_as(client, orgs.a, "student@demo.example")
    assert client.get("/api/me").json()["organisation"]["id"] == str(orgs.a)
    courses = client.get("/api/courses").json()
    assert len(courses) == 1
    assert client.get(f"/api/courses/{b_topic.course_id}/topics").status_code == 404
    assert client.get(f"/api/lessons/{b_lesson.id}").status_code == 404
    assert client.get("/api/media/private/only-b.png").status_code == 404
    topics_a = client.get(f"/api/courses/{courses[0]['id']}/topics").json()
    assert str(b_topic.id) not in {t["id"] for t in topics_a}

    sign_in_as(client, orgs.b, "admin@demo.example")
    me = client.get("/api/me").json()
    assert me["organisation"] == {"id": str(orgs.b), "name": "Other Institute"}
    assert client.get("/api/media/private/only-b.png").status_code == 200
    assert client.get(f"/api/lessons/{b_lesson.id}").status_code == 200
    assert client.get("/api/courses").json()[0]["id"] != courses[0]["id"]


def test_admin_can_queue_ping_but_student_cannot(client, orgs):
    demo_login(client, "student")
    assert client.post("/api/admin/jobs/ping").status_code == 403
    demo_login(client, "admin")
    response = client.post("/api/admin/jobs/ping")
    assert response.status_code == 202
    token = response.json()["token"]
    assert client.get(f"/api/admin/jobs/ping/{token}").json() == {"done": False, "ran_at": None}
