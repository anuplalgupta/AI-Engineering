"""The PostgreSQL job queue runs a trivial job that writes a row."""

import uuid

from ailms.platform import queue


def test_ping_job_runs_and_writes_a_row(client):
    # The client fixture opens the queue for deferring, as the web app does.
    token = queue.enqueue_ping()
    assert queue.ping_ran_at(token) is None
    queue.app.run_worker(wait=False, install_signal_handlers=False, listen_notify=False)
    assert queue.ping_ran_at(token) is not None


def test_ping_is_safe_to_run_twice():
    token = uuid.uuid4()
    queue.ping(token=str(token))
    first = queue.ping_ran_at(token)
    queue.ping(token=str(token))
    assert first is not None and queue.ping_ran_at(token) == first
