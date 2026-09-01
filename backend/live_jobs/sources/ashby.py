"""Ashby public job board API.

    https://api.ashbyhq.com/posting-api/job-board/{token}

Unauthenticated. `token` is the job board name (e.g. "ramp").
Titles sometimes carry a leading space; unlisted postings are skipped.
"""

from __future__ import annotations

from ..normalize import clean_location, clean_title, parse_posted_at
from .base import DiscoveredJob, get_json

URL = "https://api.ashbyhq.com/posting-api/job-board/{token}"


def parse_jobs(payload: object) -> list[DiscoveredJob]:
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        return []

    jobs: list[DiscoveredJob] = []

    for item in payload["jobs"]:
        if not isinstance(item, dict) or item.get("isListed") is False:
            continue

        jobs.append(
            DiscoveredJob(
                company="",
                external_job_id=item.get("id"),
                title=clean_title(item.get("title")),
                location=clean_location(item.get("location")),
                job_url=item.get("jobUrl") or item.get("applyUrl"),
                posted_at=parse_posted_at(item.get("publishedAt")),
                source="ashby",
            )
        )

    return jobs


class AshbySource:
    name = "ashby"

    def discover(self, token: str) -> list[DiscoveredJob]:
        data = get_json(URL.format(token=token))
        return parse_jobs(data)
