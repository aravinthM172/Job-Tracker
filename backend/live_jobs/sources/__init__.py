"""Registry of Live Jobs source adapters, keyed by source name."""

from .amazon import AmazonSource
from .ashby import AshbySource
from .base import DiscoveredJob, JobSource
from .greenhouse import GreenhouseSource
from .lever import LeverSource
from .oracle import OracleSource
from .swiggy import SwiggySource
from .workday import WorkdaySource

# Sources that pull large boards / need multiple requests - discovery
# runs these less often than the cheap single-request ATS feeds.
HEAVY_SOURCES = {"workday", "amazon", "oracle"}

# Sources whose feed carries no reliable "recently posted" signal - we
# show every currently-open matching req and rely on the not-seen sweep
# in close_old_jobs to retire them once they drop off the feed.
DATELESS_SOURCES = {"swiggy"}

SOURCES: dict[str, JobSource] = {
    source.name: source
    for source in (
        GreenhouseSource(),
        LeverSource(),
        AshbySource(),
        AmazonSource(),
        WorkdaySource(),
        OracleSource(),
        SwiggySource(),
    )
}

__all__ = [
    "SOURCES",
    "HEAVY_SOURCES",
    "DATELESS_SOURCES",
    "DiscoveredJob",
    "JobSource",
]
