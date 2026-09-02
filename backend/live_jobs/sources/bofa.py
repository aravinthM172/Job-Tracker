"""Bank of America careers - the AEM site's own job-search servlet.

    GET https://careers.bankofamerica.com/services/jobssearchservlet
        ?search=jobsByLocation&searchstring=India&start=0&rows=100

Unauthenticated JSON - the same feed the careers page's search box
calls. Newest-first, ``postedDate`` is ``MM/DD/YYYY``. Per-company
adapter - ``token`` unused.
"""

from __future__ import annotations

from datetime import datetime

from ..normalize import clean_location, clean_title, parse_posted_at
from .base import DiscoveredJob, get_json

SITE = "https://careers.bankofamerica.com"
URL = f"{SITE}/services/jobssearchservlet"
_PAGES = 3
_PAGE_SIZE = 100


def parse_jobs(payload: object) -> list[DiscoveredJob]:
    if not isinstance(payload, dict) or not isinstance(
        payload.get("jobsList"), list
    ):
        return []

    jobs: list[DiscoveredJob] = []

    for item in payload["jobsList"]:
        if not isinstance(item, dict):
            continue

        req_id = item.get("jobRequisitionId")
        where = ", ".join(
            part
            for part in (item.get("city"), item.get("state"), item.get("country"))
            if part
        )
        path = item.get("jcrURL") or ""

        jobs.append(
            DiscoveredJob(
                company="Bank of America",
                external_job_id=str(req_id) if req_id else None,
                title=clean_title(item.get("postingTitle")),
                location=clean_location(where),
                job_url=(SITE + path) if path.startswith("/") else (path or None),
                posted_at=parse_posted_at(item.get("postedDate")),
                source="bofa",
            )
        )

    return jobs


class BofaSource:
    name = "bofa"

    def discover(self, token: str = "") -> list[DiscoveredJob]:
        jobs: list[DiscoveredJob] = []

        for page in range(_PAGES):
            data = get_json(
                URL,
                params={
                    "search": "jobsByLocation",
                    "searchstring": "India",
                    "start": page * _PAGE_SIZE,
                    "rows": _PAGE_SIZE,
                },
            )
            batch = parse_jobs(data)
            if not batch:
                break

            jobs.extend(batch)

            if all(_is_old(job.posted_at) for job in batch):
                break

        return jobs


def _is_old(posted_at: datetime | None) -> bool:
    if posted_at is None:
        return True
    return (datetime.utcnow() - posted_at).days > 3
