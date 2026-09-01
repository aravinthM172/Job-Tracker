"""Registry of Live Jobs source adapters, keyed by source name."""

from .amazon import AmazonSource
from .ashby import AshbySource
from .base import DiscoveredJob, JobSource
from .greenhouse import GreenhouseSource
from .lever import LeverSource

SOURCES: dict[str, JobSource] = {
    source.name: source
    for source in (
        GreenhouseSource(),
        LeverSource(),
        AshbySource(),
        AmazonSource(),
    )
}

__all__ = ["SOURCES", "DiscoveredJob", "JobSource"]
