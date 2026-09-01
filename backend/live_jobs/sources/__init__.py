"""Registry of Live Jobs source adapters, keyed by source name."""

from .amazon import AmazonSource
from .ashby import AshbySource
from .base import DiscoveredJob, JobSource
from .greenhouse import GreenhouseSource
from .lever import LeverSource
from .workday import WorkdaySource

# Sources that pull large boards / need multiple requests - discovery
# runs these less often than the cheap single-request ATS feeds.
HEAVY_SOURCES = {"workday", "amazon"}

SOURCES: dict[str, JobSource] = {
    source.name: source
    for source in (
        GreenhouseSource(),
        LeverSource(),
        AshbySource(),
        AmazonSource(),
        WorkdaySource(),
    )
}

__all__ = ["SOURCES", "HEAVY_SOURCES", "DiscoveredJob", "JobSource"]
