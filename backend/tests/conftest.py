"""Backend-level test setup.

Runs before any test module imports ``db`` / ``auth`` / ``main``:
- point the DB at a throwaway dir so tests never touch the real file;
- configure an owner so the session-auth middleware is active (the
  auth + role-gate tests need it; nothing else here depends on it).
"""

import os
import tempfile

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="backend-tests-"))
os.environ.setdefault("OWNER_USERNAME", "owner")
os.environ.setdefault("OWNER_PASSWORD", "test-owner-pw-123")
os.environ.setdefault("COOKIE_SECURE", "0")
