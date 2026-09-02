"""SmartRecruiters public postings API.

    https://api.smartrecruiters.com/v1/companies/{token}/postings
        ?limit=100&offset=0&country=in

Unauthenticated - the same feed a company's SmartRecruiters-hosted
careers page calls. ``token`` is the SmartRecruiters company id
(e.g. "ServiceNow"). ``releasedDate`` is a real ISO timestamp. The feed
is newest-first, so paging stops once a page is entirely out of window.
"""

from __future__ import annotations

import re
from datetime import datetime

from ..normalize import clean_location, clean_title, parse_posted_at
from .base import DiscoveredJob, get_json

API = "https://api.smartrecruiters.com/v1/companies/{token}/postings"
VIEW = "https://jobs.smartrecruiters.com/{token}/{job_id}"

_PAGES = 3
_PAGE_SIZE = 100


def parse_jobs(payload: object, token: str = "") -> list[DiscoveredJob]:
    if not isinstance(payload, dict) or not isinstance(
        payload.get("content"), list
    ):
        return []

    jobs: list[DiscoveredJob] = []

    for item in payload["content"]:
        if not isinstance(item, dict):
            continue

        job_id = item.get("id")
        location = item.get("location") or {}
        # fullLocation reads "City, Region, Country" but collapses to
        # "City, , Country" when region is blank - tidy the empty middle.
        where = location.get("fullLocation") or ", ".join(
            part
            for part in (location.get("city"), location.get("country"))
            if part
        )
        if where:
            where = re.sub(r",\s*,", ",", where)

        jobs.append(
            DiscoveredJob(
                company="",
                external_job_id=str(job_id) if job_id else None,
                title=clean_title(item.get("name")),
                location=clean_location(where),
                job_url=(
                    VIEW.format(token=token, job_id=job_id)
                    if job_id and token
                    else None
                ),
                posted_at=parse_posted_at(item.get("releasedDate")),
                source="smartrecruiters",
            )
        )

    return jobs


class SmartRecruitersSource:
    name = "smartrecruiters"

    def discover(self, token: str) -> list[DiscoveredJob]:
        jobs: list[DiscoveredJob] = []

        for page in range(_PAGES):
            data = get_json(
                API.format(token=token),
                params={
                    "limit": _PAGE_SIZE,
                    "offset": page * _PAGE_SIZE,
                    "country": "in",
                },
            )
            batch = parse_jobs(data, token)
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
