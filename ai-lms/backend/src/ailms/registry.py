"""Imports every table definition, so that Base.metadata is complete.

Used by the migrations and by anything that needs the whole schema.
"""

import ailms.catalog.api  # noqa: F401
import ailms.content.api  # noqa: F401
import ailms.identity.api  # noqa: F401
import ailms.platform.audit  # noqa: F401
import ailms.platform.queue  # noqa: F401
from ailms.platform.db import Base

metadata = Base.metadata
