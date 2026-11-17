"""Start-up preparation is safe to run again and from two containers at once."""

import threading

from sqlalchemy import func, select

from ailms import bootstrap
from ailms.catalog.models import Topic
from ailms.identity.models import Organisation
from ailms.platform.db import session_scope, system_scope


def test_prepare_twice_at_once_loads_one_copy(store):
    errors: list[Exception] = []

    def run() -> None:
        try:
            bootstrap.prepare()
        except Exception as error:  # noqa: BLE001
            errors.append(error)

    threads = [threading.Thread(target=run) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)
    assert errors == []
    with session_scope() as session, system_scope(session):
        assert session.scalar(select(func.count()).select_from(Organisation)) == 1
        assert session.scalar(select(func.count()).select_from(Topic)) > 0
    assert store.objects
