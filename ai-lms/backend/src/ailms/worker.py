"""The worker's entry point: the queue with every module's jobs registered.

    procrastinate --app=ailms.worker.app worker
"""

import ailms.identity.api  # noqa: F401  (registers the identity jobs)
from ailms.platform.queue import app

__all__ = ["app"]
