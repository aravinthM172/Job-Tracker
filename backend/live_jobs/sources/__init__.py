"""Registry of Live Jobs source adapters, keyed by source name."""

from .adzuna import AdzunaSource
from .amazon import AmazonSource
from .ashby import AshbySource
from .avature import AvatureSource
from .base import DiscoveredJob, JobSource
from .bofa import BofaSource
from .browser import BrowserSource
from .darwinbox import DarwinboxSource
from .eightfold import EightfoldSource
from .goldman import GoldmanSource
from .google import GoogleSource
from .greenhouse import GreenhouseSource
from .keka import KekaSource
from .lever import LeverSource
from .meta import MetaSource
from .oracle import OracleSource
from .phenom import PhenomSource
from .radancy import RadancySource
from .sitemap import SitemapSource
from .smartrecruiters import SmartRecruitersSource
from .successfactors import SuccessFactorsSource
from .mynexthire import MyNextHireSource
from .workday import WorkdaySource

# Sources that pull large boards / need multiple requests - discovery
# runs these less often than the cheap single-request ATS feeds.
HEAVY_SOURCES = {
    "workday",
    "amazon",
    "oracle",
    "radancy",
    "sitemap",
    "browser",
    "successfactors",
    "eightfold",
    "phenom",
    "goldman",
    "avature",
    "adzuna",  # external quota - keep off the every-cycle path
}

# Sources behind aggressive anti-scraping (Google / Meta), or that spin
# up a headless browser (browser). Run them on the slowest cadence.
GUARDED_SOURCES = {"google", "meta", "browser"}

# Sources whose feed carries no reliable "recently posted" signal - we
# show every currently-open matching req and rely on the not-seen sweep
# in close_old_jobs to retire them once they drop off the feed.
DATELESS_SOURCES = {"mynexthire", "goldman", "meta", "google", "browser", "successfactors"}

SOURCES: dict[str, JobSource] = {
    source.name: source
    for source in (
        AdzunaSource(),
        GreenhouseSource(),
        LeverSource(),
        AshbySource(),
        AvatureSource(),
        AmazonSource(),
        WorkdaySource(),
        OracleSource(),
        SmartRecruitersSource(),
        RadancySource(),
        MyNextHireSource(),
        MetaSource(),
        PhenomSource(),
        GoldmanSource(),
        GoogleSource(),
        BofaSource(),
        KekaSource(),
        DarwinboxSource(),
        EightfoldSource(),
        SitemapSource(),
        BrowserSource(),
        SuccessFactorsSource(),
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
