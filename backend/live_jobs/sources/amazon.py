"""Amazon jobs search (amazon.jobs).

    https://www.amazon.jobs/en/search.json?sort=recent&result_limit=100&offset=0

Unauthenticated - the JSON the amazon.jobs search page itself calls.
This is a per-company adapter (Amazon runs its own careers site rather
than a shared ATS). `token` is an optional free-text query filter.
`posted_date` is a human date ("September 1, 2026") - day granularity.
"""

from __future__ import annotations

from datetime import datetime

from ..normalize import (
    clean_description,
    clean_location,
    clean_title,
    parse_posted_at,
)
from .base import DiscoveredJob, get_json

SITE = "https://www.amazon.jobs"
URL = f"{SITE}/en/search.json"
_PAGES = 6
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
                # without this the 400 newest reqs are ~95% non-India and
                # only a handful of Bengaluru ones survive the location
                # filter. country=IND -> ~2.4k India reqs, newest first.
                "country": "IND",
            }
            if token:
                params["base_query"] = token

            data = get_json(URL, params=params)
            page_jobs = parse_jobs(data)

            if not page_jobs:
                break

            jobs.extend(page_jobs)

            # sort=recent is newest-first; once a whole page is out of
            # window there's no point paging deeper.
            if all(_is_old(job.posted_at) for job in page_jobs):
                break

        return jobs


def _is_old(posted_at: datetime | None) -> bool:
    if posted_at is None:
        return False  # keep undated reqs; discovery decides
    return (datetime.utcnow() - posted_at).days > 3
