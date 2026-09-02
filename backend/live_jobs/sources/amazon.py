"""Amazon jobs search (amazon.jobs).

    https://www.amazon.jobs/en/search.json?sort=recent&result_limit=100&offset=0

Unauthenticated - the JSON the amazon.jobs search page itself calls.
This is a per-company adapter (Amazon runs its own careers site rather
than a shared ATS). `token` is an optional free-text query filter.
`posted_date` is a human date ("September 1, 2026") - day granularity.
"""

from __future__ import annotations

from ..normalize import (
    clean_description,
    clean_location,
    clean_title,
    parse_posted_at,
)
from .base import DiscoveredJob, get_json

SITE = "https://www.amazon.jobs"
URL = f"{SITE}/en/search.json"
_PAGES = 4
_PAGE_SIZE = 100


def parse_jobs(payload: object) -> list[DiscoveredJob]:
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        return []

    jobs: list[DiscoveredJob] = []

    for item in payload["jobs"]:
        if not isinstance(item, dict):
            continue

        path = item.get("job_path") or ""
        external = item.get("id_icims") or item.get("id")

        jobs.append(
            DiscoveredJob(
                company="Amazon",
                external_job_id=str(external) if external else None,
                title=clean_title(item.get("title")),
                location=clean_location(
                    item.get("normalized_location") or item.get("location")
                ),
                job_url=(SITE + path) if path else item.get("url_next_step"),
                posted_at=parse_posted_at(item.get("posted_date")),
                description=clean_description(
                    " ".join(
                        str(item.get(field) or "")
                        for field in (
                            "description",
                            "basic_qualifications",
                            "preferred_qualifications",
                        )
                    )
                ),
                source="amazon",
            )
        )

    return jobs


class AmazonSource:
    name = "amazon"

    def discover(self, token: str = "") -> list[DiscoveredJob]:
        jobs: list[DiscoveredJob] = []

        for page in range(_PAGES):
            params = {
                "sort": "recent",
                "result_limit": _PAGE_SIZE,
                "offset": page * _PAGE_SIZE,
            }
            if token:
                params["base_query"] = token

            data = get_json(URL, params=params)
            page_jobs = parse_jobs(data)

            if not page_jobs:
                break

            jobs.extend(page_jobs)

        return jobs
