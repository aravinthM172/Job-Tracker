"""Registry of Live Jobs source adapters, keyed by source name."""

from .amazon import AmazonSource
from .ashby import AshbySource
from .base import DiscoveredJob, JobSource
from .bofa import BofaSource
from .darwinbox import DarwinboxSource
from .google import GoogleSource
from .greenhouse import GreenhouseSource
from .keka import KekaSource
from .lever import LeverSource
from .meta import MetaSource
from .oracle import OracleSource
from .radancy import RadancySource
from .sitemap import SitemapSource
from .smartrecruiters import SmartRecruitersSource
from .swiggy import SwiggySource
from .workday import WorkdaySource

# Sources that pull large boards / need multiple requests - discovery
# runs these less often than the cheap single-request ATS feeds.
HEAVY_SOURCES = {"workday", "amazon", "oracle", "radancy", "sitemap"}

# Sources behind aggressive anti-scraping (Google / Meta). Run them on
# the slowest cadence - a burst gets the host IP soft-blocked, and a
# block looks like an empty feed rather than an error.
GUARDED_SOURCES = {"google", "meta"}

# Sources whose feed carries no reliable "recently posted" signal - we
# show every currently-open matching req and rely on the not-seen sweep
# in close_old_jobs to retire them once they drop off the feed.
DATELESS_SOURCES = {"swiggy", "meta", "google"}

SOURCES: dict[str, JobSource] = {
    source.name: source
    for source in (
        GreenhouseSource(),
        LeverSource(),
        AshbySource(),
        AmazonSource(),
        WorkdaySource(),
        OracleSource(),
        SmartRecruitersSource(),
        RadancySource(),
        SwiggySource(),
        MetaSource(),
        GoogleSource(),
        BofaSource(),
        KekaSource(),
        DarwinboxSource(),
        SitemapSource(),
    )
}

__all__ = [
    "SOURCES",
    "HEAVY_SOURCES",
    "GUARDED_SOURCES",
    "DATELESS_SOURCES",
    "DiscoveredJob",
    "JobSource",
]
