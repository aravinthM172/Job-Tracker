"""Live Jobs subsystem.

Importing this package ensures the ``live_jobs`` table exists, regardless
of import order relative to ``db`` (whose own ``create_all`` runs before
this model is registered).
"""

from db import engine
from db_base import Base

from . import models  # noqa: F401  - registers LiveJob on Base.metadata


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


init_db()
