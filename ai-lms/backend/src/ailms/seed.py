"""Loads the sample data on first start.

Ids are derived from the organisation slug and the slugs in the seed files, so an
empty database always gets exactly the same rows, and a second organisation
loaded from the same files gets rows of its own. Anything that already exists is
left alone, so loading twice changes nothing.
"""

import json
import logging
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ailms.catalog.api import TopicSpec, import_course
from ailms.content.api import import_tutorial
from ailms.identity.api import (
    Role,
    any_organisation_exists,
    ensure_organisation,
    ensure_user,
    organisation_id_by_slug,
)
from ailms.platform.db import scope_to_organisation, session_scope
from ailms.platform.settings import get_settings
from ailms.platform.storage import Storage, get_storage, organisation_key, store_file

log = logging.getLogger(__name__)

_NAMESPACE = uuid.UUID("6f0b3c52-8a1e-4d55-9a57-2f1d3e6f7a10")


def seed_id(kind: str, slug: str) -> uuid.UUID:
    return uuid.uuid5(_NAMESPACE, f"{kind}:{slug}")


def read_seed(data_dir: Path | None = None) -> dict[str, Any]:
    data_dir = data_dir or get_settings().sample_data_dir
    return json.loads((data_dir / "course.json").read_text(encoding="utf-8"))


def load_sample_data(
    session: Session,
    data_dir: Path | None = None,
    storage: Storage | None = None,
    *,
    organisation_slug: str | None = None,
    organisation_name: str | None = None,
) -> uuid.UUID:
    """Load the sample course into the given session. Returns the organisation id.

    organisation_slug and organisation_name replace the ones in the seed file; tests
    use them to load the same course into a second organisation.
    """
    data_dir = data_dir or get_settings().sample_data_dir
    storage = storage or get_storage()
    seed = read_seed(data_dir)

    slug = organisation_slug or seed["organisation"]["slug"]
    organisation_id = ensure_organisation(
        session,
        organisation_id=seed_id("organisation", slug),
        slug=slug,
        name=organisation_name or seed["organisation"]["name"],
    )
    scope_to_organisation(session, organisation_id)

    def sid(kind: str, key: str) -> uuid.UUID:
        return seed_id(kind, f"{slug}/{key}")

    for account in seed["accounts"]:
        ensure_user(
            session,
            user_id=sid("user", account["email"]),
            email=account["email"],
            display_name=account["display_name"],
            role=Role(account["role"]),
            is_demo=True,
        )

    course = seed["course"]
    topic_id = {t["slug"]: sid("topic", f"{course['slug']}/{t['slug']}") for t in course["topics"]}
    import_course(
        session,
        programme_id=sid("programme", seed["programme"]["slug"]),
        programme_title=seed["programme"]["title"],
        course_id=sid("course", course["slug"]),
        course_title=course["title"],
        subject=course["subject"],
        level=course["level"],
        topics=[
            TopicSpec(
                id=topic_id[t["slug"]],
                title=t["title"],
                position=t["position"],
                parent_id=topic_id[t["parent"]] if t["parent"] else None,
                prerequisite_ids=[topic_id[p] for p in t["prerequisites"]],
            )
            for t in course["topics"]
        ],
    )

    restore_missing_media(organisation_id, data_dir, storage)

    for item in seed["lessons"]:
        lesson = json.loads((data_dir / item["file"]).read_text(encoding="utf-8"))
        import_tutorial(
            session,
            lesson_id=sid("lesson", item["slug"]),
            version_id=sid("lesson_version", f"{item['slug']}/1"),
            topic_id=topic_id[item["topic"]],
            title=lesson["title"],
            document=lesson["document"],
            estimated_minutes=lesson["estimated_minutes"],
            attribution=lesson.get("attribution"),
            publish=True,
            comment="Included sample data",
        )
    return organisation_id


def restore_missing_media(
    organisation_id: uuid.UUID, data_dir: Path | None = None, storage: Storage | None = None
) -> None:
    """Put back sample images that are missing from the object store."""
    data_dir = data_dir or get_settings().sample_data_dir
    storage = storage or get_storage()
    for item in read_seed(data_dir)["media"]:
        key = organisation_key(organisation_id, item["key"])
        if not storage.exists(key):
            store_file(storage, key, (data_dir / item["file"]).read_bytes(), item["content_type"])


def main() -> None:
    """Load the sample data if the database has no organisation yet."""
    with session_scope() as session:
        if any_organisation_exists(session):
            existing = organisation_id_by_slug(
                session, get_settings().default_organisation_slug
            )
            if existing is not None:
                restore_missing_media(existing)
            log.info("the database already has data; sample data not loaded again")
            return
        load_sample_data(session)
    log.info("sample data loaded")
