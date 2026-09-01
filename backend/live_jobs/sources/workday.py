"""Workday CXS public job feed.

    POST https://{tenant}.{host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs

Unauthenticated. ``token`` is ``"tenant/host/site"`` e.g.
``"nvidia/wd5/NVIDIAExternalCareerSite"``.

The list endpoint only gives a relative ``postedOn`` ("Posted Today",
"Posted 5 Days Ago"), so in practice only Today / Yesterday postings
survive the 48h gate - which is exactly what we want here.
"""

from __future__ import annotations

import re
from datetime import datetime

from ..normalize import clean_location, clean_title, parse_posted_at
from .base import DiscoveredJob, get_json

CXS = "https://{tenant}.{host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
VIEW = "https://{tenant}.{host}.myworkdayjobs.com/en-US/{site}{path}"

_PAGES = 3
_PAGE_SIZE = 20
_REQ_ID = re.compile(r"_([A-Za-z0-9][A-Za-z0-9.\-]*)$")


def _split(token: str) -> tuple[str, str, str] | None:
    parts = token.split("/")
    return (parts[0], parts[1], parts[2]) if len(parts) == 3 else None


def parse_jobs(payload: object, token: str = "") -> list[DiscoveredJob]:
    if not isinstance(payload, dict) or not isinstance(
        payload.get("jobPostings"), list
    ):
        return []

    parts = _split(token)
    tenant, host, site = parts or ("", "", "")

    jobs: list[DiscoveredJob] = []

    for item in payload["jobPostings"]:
        if not isinstance(item, dict):
            continue

        path = item.get("externalPath") or ""
        bullets = item.get("bulletFields") or []
        req_id = bullets[0] if bullets else None
        if not req_id:
            match = _REQ_ID.search(path)
            req_id = match.group(1) if match else None

        jobs.append(
            DiscoveredJob(
                company="",
                external_job_id=req_id,
                title=clean_title(item.get("title")),
                location=clean_location(item.get("locationsText")),
                job_url=(
                    VIEW.format(tenant=tenant, host=host, site=site, path=path)
                    if path and tenant
                    else None
                ),
                posted_at=parse_posted_at(item.get("postedOn")),
                source="workday",
            )
        )

    return jobs


class WorkdaySource:
    name = "workday"

    def discover(self, token: str) -> list[DiscoveredJob]:
        parts = _split(token)
        if parts is None:
            return []

        tenant, host, site = parts
        url = CXS.format(tenant=tenant, host=host, site=site)

        jobs: list[DiscoveredJob] = []

        for page in range(_PAGES):
            data = get_json(
                url,
                json_body={
                    "appliedFacets": {},
                    "limit": _PAGE_SIZE,
                    "offset": page * _PAGE_SIZE,
                    "searchText": "",
                },
            )
            batch = parse_jobs(data, token)
            if not batch:
                break

            jobs.extend(batch)

            # Results aren't reliably date-sorted, but once a whole page
            # is old there's little point paging deeper.
            if all(_is_old(job.posted_at) for job in batch):
                break

        return jobs


def _is_old(posted_at: datetime | None) -> bool:
    if posted_at is None:
        return True
    return (datetime.utcnow() - posted_at).days > 3
