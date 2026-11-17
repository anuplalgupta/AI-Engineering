"""Public interface of the catalog module. Other modules import from here only.

Only service functions and plain data types are exported, never the tables (ORM
classes): other modules must go through the catalog's own rules.
"""

from ailms.catalog.routes import router
from ailms.catalog.service import TopicSpec, import_course

__all__ = [
    "TopicSpec",
    "import_course",
    "router",
]
