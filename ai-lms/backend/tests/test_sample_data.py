"""The sample data: complete, valid, original and loaded only once."""

import json
import re

from sqlalchemy import func, select

from ailms import seed
from ailms.catalog.models import Topic, TopicPrerequisite
from ailms.content.api import LessonDocument
from ailms.content.models import Lesson, LessonVersion
from ailms.identity.models import User
from ailms.platform.audit import StatusChange
from ailms.platform.db import scope_to_organisation, session_scope
from ailms.platform.settings import get_settings
from ailms.platform.svg import clean_svg

DATA = get_settings().sample_data_dir


def _counts(organisation_id):
    with session_scope() as session:
        scope_to_organisation(session, organisation_id)
        return {
            model.__tablename__: session.scalar(select(func.count()).select_from(model))
            for model in (User, Topic, TopicPrerequisite, Lesson, LessonVersion, StatusChange)
        }


def test_loading_twice_changes_nothing(orgs, store):
    before = _counts(orgs.a)
    objects = dict(store.objects)
    with session_scope() as session:
        assert seed.load_sample_data(session, storage=store) == orgs.a
    assert _counts(orgs.a) == before
    assert store.objects == objects
    assert before["user_account"] == 3
    assert 8 <= before["topic"] - 2 <= 12  # topics, plus the two chapter headings
    assert before["topic_prerequisite"] >= 8
    assert before["lesson"] == 1


def test_seed_main_does_not_load_again(orgs):
    before = _counts(orgs.a)
    seed.main()
    assert _counts(orgs.a) == before


def test_prerequisites_form_no_loop():
    course = seed.read_seed(DATA)["course"]
    needs = {t["slug"]: set(t["prerequisites"]) for t in course["topics"]}
    done: set[str] = set()
    while needs:
        ready = [slug for slug, pre in needs.items() if pre <= done]
        assert ready, f"loop among {sorted(needs)}"
        for slug in ready:
            done.add(slug)
            del needs[slug]


def _lesson() -> dict:
    item = seed.read_seed(DATA)["lessons"][0]
    return json.loads((DATA / item["file"]).read_text(encoding="utf-8"))


def _texts(section: dict) -> list[str]:
    return (
        [section.get("body_md") or ""]
        + [step["body_md"] for step in section.get("steps", [])]
        + section.get("items", [])
    )


def test_tutorial_is_valid_and_the_right_length():
    lesson = _lesson()
    LessonDocument.model_validate(lesson["document"])
    text = " ".join(t for s in lesson["document"]["sections"] for t in _texts(s))
    words = len(text.split())
    assert 600 <= words <= 1000, words
    maths = re.findall(r"\$\$.+?\$\$|\$[^$]+\$", text, flags=re.S)
    assert len(maths) >= 10
    assert all(s["sources"] for s in lesson["document"]["sections"])
    assert "OpenStax University Physics Volume 1" in lesson["attribution"]
    assert "CC BY 4.0" in lesson["attribution"] and "original" in lesson["attribution"]


def test_dollar_signs_are_balanced():
    for section in _lesson()["document"]["sections"]:
        for text in _texts(section):
            assert text.count("$") % 2 == 0, (section["id"], text[:60])


def test_sample_svg_is_clean():
    svg = (DATA / "images" / "vector-components.svg").read_bytes()
    assert b"<script" not in svg
    assert b"<title" in clean_svg(svg)
