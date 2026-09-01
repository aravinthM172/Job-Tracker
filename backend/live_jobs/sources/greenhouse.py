"""Greenhouse public job board API.

    https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true

Unauthenticated - this is the same JSON a company's Greenhouse-hosted
careers page fetches. `token` is the board slug (e.g. "gitlab").
"""

from __future__ import annotations

from ..normalize import clean_location, clean_title, parse_posted_at
from .base import DiscoveredJob, get_json

URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


def parse_jobs(payload: object) -> list[DiscoveredJob]:
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        return []

    jobs: list[DiscoveredJob] = []

    for item in payload["jobs"]:
        if not isinstance(item, dict):
            continue

        job_id = item.get("id")
        location = item.get("location") or {}

        jobs.append(
            DiscoveredJob(
                company="",
                external_job_id=str(job_id) if job_id is not None else None,
                title=clean_title(item.get("title")),
                location=clean_location(location.get("name")),
                job_url=item.get("absolute_url"),
                posted_at=parse_posted_at(
                    item.get("first_published") or item.get("updated_at")
                ),
                source="greenhouse",
            )
        )

    return jobs


class GreenhouseSource:
    name = "greenhouse"

    def discover(self, token: str) -> list[DiscoveredJob]:
        data = get_json(URL.format(token=token), params={"content": "true"})
        return parse_jobs(data)
