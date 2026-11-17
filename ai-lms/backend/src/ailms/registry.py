"""Imports every table definition, so that Base.metadata is complete.

Used by the migrations and by anything that needs the whole schema. This is the one
place outside a module allowed to import its models (see pyproject.toml).
"""

import ailms.catalog.models  # noqa: F401
import ailms.content.models  # noqa: F401
import ailms.identity.models  # noqa: F401
import ailms.platform.audit  # noqa: F401
import ailms.platform.queue  # noqa: F401
import ailms.platform.ratelimit  # noqa: F401
from ailms.platform.db import Base

metadata = Base.metadata
