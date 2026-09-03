"""Point the app DB at a throwaway directory before ``db`` is imported,
so the backend-level tests never touch the real ``job_tracker.sqlite3``.
"""

import os
import tempfile

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="backend-tests-"))
