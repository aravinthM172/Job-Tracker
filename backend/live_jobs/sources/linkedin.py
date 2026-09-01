"""LinkedIn source - placeholder.

LinkedIn has no compliant unauthenticated jobs feed, so this stays empty.
Real coverage comes from the ATS adapters (greenhouse/lever/ashby) and
per-company adapters (amazon, ...). Kept only so the intent is on record.
"""

from __future__ import annotations

from .base import DiscoveredJob


class LinkedInSource:
    name = "linkedin"

    def discover(self, token: str) -> list[DiscoveredJob]:
        return []
