from dataclasses import dataclass
from datetime import datetime


@dataclass
class DiscoveredJob:
    company: str
    external_job_id: str | None
    title: str
    location: str | None
    job_url: str | None
    posted_at: datetime | None
    description: str | None = None
    source: str = "linkedin"


class LinkedInSource:
    name = "linkedin"

    def discover_company_jobs(
        self,
        company: str,
    ) -> list[DiscoveredJob]:
        """
        Source adapter.

        The compliant LinkedIn discovery mechanism will be
        connected here. Keep the rest of Live Jobs independent
        from the source implementation.
        """
        return []
