"""Public interface of the catalog module. Other modules import from here only."""

from ailms.catalog.models import Course, Programme, Topic, TopicPrerequisite
from ailms.catalog.routes import router
from ailms.catalog.service import TopicSpec, import_course, list_prerequisites, list_topics

__all__ = [
    "Course",
    "Programme",
    "Topic",
    "TopicPrerequisite",
    "TopicSpec",
    "import_course",
    "list_prerequisites",
    "list_topics",
    "router",
]
