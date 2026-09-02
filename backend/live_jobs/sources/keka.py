"""Keka-hosted careers pages ({tenant}.keka.com/careers).

    GET https://{tenant}.keka.com/careers/api/embedjobs/default/active/{portal_id}

Unauthenticated JSON - the feed the Keka careers SPA calls. ``token`` is
``"{tenant}|{portal_id}"`` (the portal id is the UUID in the embed-jobs
API path, visible in the careers page's network calls). ``publishedOn``
is ISO 8601. Keka is common for Indian startups.
"""

from __future__ import annotations

from ..normalize import clean_location, clean_title, parse_posted_at
from .base import DiscoveredJob, get_json

API = "https://{tenant}.keka.com/careers/api/embedjobs/default/active/{portal}"
VIEW = "https://{tenant}.keka.com/careers/jobdetails/{job_id}"


def parse_jobs(payload: object, token: str = "") -> list[DiscoveredJob]:
    if not isinstance(payload, list):
        return []

    tenant = token.split("|", 1)[0]

    jobs: list[DiscoveredJob] = []

    for item in payload:
        if not isinstance(item, dict):
            continue

        job_id = item.get("id")
        locs = item.get("jobLocations")
        where = None
        if isinstance(locs, list) and locs and isinstance(locs[0], dict):
            first = locs[0]
            where = ", ".join(
                part
                for part in (
                    first.get("city") or first.get("name"),
                    first.get("state"),
                    first.get("countryName"),
                )
                if part
            )

        jobs.append(
            DiscoveredJob(
                company="",
                external_job_id=str(job_id) if job_id is not None else None,
                title=clean_title(item.get("title")),
                location=clean_location(where),
                job_url=(
                    VIEW.format(tenant=tenant, job_id=job_id)
                    if job_id is not None and tenant
                    else None
                ),
                posted_at=parse_posted_at(item.get("publishedOn")),
                source="keka",
            )
        )

    return jobs


class KekaSource:
    name = "keka"

    def discover(self, token: str) -> list[DiscoveredJob]:
        tenant, _, portal = token.partition("|")
        if not portal:
            return []

        data = get_json(API.format(tenant=tenant, portal=portal))
        return parse_jobs(data, token)
