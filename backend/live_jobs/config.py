"""Runtime config for Live Jobs discovery.

The location filter keeps the dashboard focused on a set of metros.
Override at deploy time without a code change:

    LIVE_JOBS_LOCATIONS="bengaluru,hyderabad,..."   # default (below)
    LIVE_JOBS_LOCATIONS="india"                     # whole country
    LIVE_JOBS_LOCATIONS=""                          # no filter

A posting is kept when its (lower-cased) location text contains any of
the listed fragments. Postings whose feed gives no usable location are
dropped while a filter is active.
"""

from __future__ import annotations

import os

# Bengaluru + Hyderabad, with the spellings / state names / airport
# codes the various ATS feeds use.
_DEFAULT = (
    "bengaluru,bangalore,bengaluroo,bangaluru,karnataka,"
    "hyderabad,hyderabaad,secunderabad,telangana"
)


def location_filter() -> list[str]:
    raw = os.getenv("LIVE_JOBS_LOCATIONS", _DEFAULT)
    return [fragment.strip().lower() for fragment in raw.split(",") if fragment.strip()]


def location_matches(location: str | None, fragments: list[str]) -> bool:
    if not fragments:
        return True
    if not location:
        return False
    text = location.lower()
    return any(fragment in text for fragment in fragments)
