"""Phenom People career sites (the "refineSearch" widget API).

    POST https://{host}/widgets
        {..., "ddoKey": "refineSearch", "selected_fields": {"country": ["India"]},
         "from": {offset}, "size": 50, "keywords": "", "global": true}

Unauthenticated - the same JSON the Phenom-hosted careers page calls.
``token`` is just the host, e.g. ``"careers.cisco.com"``. The feed's
sort is unreliable, so this pulls every India posting (paged) and lets
the 48h window + location filter in discovery do the narrowing.
``jobId`` is stable; ``postedDate`` is ISO 8601.
"""

from __future__ import annotations

from ..normalize import (
    clean_description,
    clean_location,
    clean_title,
    parse_posted_at,
)
from .base import DiscoveredJob, get_json

_PAGE_SIZE = 50
_MAX_PAGES = 6  # up to 300 India reqs; discovery drops the out-of-window ones


def _body(offset: int) -> dict:
    return {
        "lang": "en_global",
        "deviceType": "desktop",
        "country": "global",
        "pageName": "search-results",
        "ddoKey": "refineSearch",
        "sortBy": "Most recent",
        "subsearch": "",
        "from": offset,
        "jobs": True,
        "counts": False,
        "all_fields": ["country", "city", "state", "category"],
        "size": _PAGE_SIZE,
        "clearAll": False,
        "jdsource": "facets",
        "isSliderEnable": False,
        "keywords": "",
        "global": True,
        "selected_fields": {"country": ["India"]},
        "locationData": {},
    }


def _jobs(payload: object) -> list:
    if not isinstance(payload, dict):
        return []
    refine = payload.get("refineSearch")
    data = refine.get("data") if isinstance(refine, dict) else None
    jobs = data.get("jobs") if isinstance(data, dict) else None
    return jobs if isinstance(jobs, list) else []


def parse_jobs(payload: object, host: str = "") -> list[DiscoveredJob]:
    jobs: list[DiscoveredJob] = []

    for item in _jobs(payload):
        if not isinstance(item, dict):
            continue

        location = clean_location(
            item.get("location")
            or item.get("cityStateCountry")
            or ", ".join(
                str(x)
                for x in (item.get("city"), item.get("state"), item.get("country"))
                if x
            )
        )

        job_url = item.get("applyUrl") or (
            f"https://{host}/global/en/job/{item.get('jobId')}"
            if host and item.get("jobId")
            else None
        )
        # applyUrl often points straight at the ATS /apply page - trim it
        if job_url and job_url.endswith("/apply"):
            job_url = job_url[: -len("/apply")]

        job_id = item.get("jobId") or item.get("reqId")

        jobs.append(
            DiscoveredJob(
                company="",
                external_job_id=str(job_id) if job_id is not None else None,
                title=clean_title(item.get("title")),
                location=location,
                job_url=job_url,
                posted_at=parse_posted_at(
                    item.get("postedDate") or item.get("dateCreated")
                ),
                description=clean_description(item.get("descriptionTeaser")),
                source="phenom",
            )
        )

    return jobs


class PhenomSource:
    name = "phenom"

    def discover(self, token: str) -> list[DiscoveredJob]:
        host = token.strip().strip("/")
        if not host or "." not in host:
            return []

        url = f"https://{host}/widgets"
        jobs: list[DiscoveredJob] = []

        for page in range(_MAX_PAGES):
            data = get_json(url, json_body=_body(page * _PAGE_SIZE))
            batch = parse_jobs(data, host)
            if not batch:
                break
            jobs.extend(batch)
            if len(batch) < _PAGE_SIZE:
                break

        return jobs
