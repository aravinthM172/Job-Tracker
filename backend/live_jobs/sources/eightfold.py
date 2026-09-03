"""Eightfold "PCS X" career sites.

    GET https://{host}/api/pcsx/search
        ?domain={domain}&location=Bengaluru, India
        &start={offset}&num=10&sort_by=timestamp

Unauthenticated - the same JSON the Eightfold-hosted careers page calls.
``token`` is ``"host|domain"`` e.g.
``"apply.careers.microsoft.com|microsoft.com"``. ``num`` is capped at 10
server-side; results are newest-first so paging stops on the first
fully-old page. The list carries an epoch ``postedTs`` but no body - the
per-position detail endpoint fills the description for the newest few.
"""

from __future__ import annotations

import re
from datetime import datetime

from ..normalize import (
    clean_description,
    clean_location,
    clean_title,
    parse_posted_at,
)
from .base import DiscoveredJob, get_json

SEARCH = "https://{host}/api/pcsx/search"
DETAIL = "https://{host}/api/pcsx/position_details"

_PAGES = 4
_PAGE_SIZE = 10
_ENRICH_MAX = 12
_LOCATIONS = ("Bengaluru, India", "Hyderabad, India")


def _positions(payload: object) -> list:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("positions"), list):
        return data["positions"]
    if isinstance(payload.get("positions"), list):
        return payload["positions"]
    return []


def parse_jobs(payload: object, token: str = "") -> list[DiscoveredJob]:
    host, _, _domain = token.partition("|")
    jobs: list[DiscoveredJob] = []

    for item in _positions(payload):
        if not isinstance(item, dict):
            continue

        locations = item.get("locations")
        location = None
        if isinstance(locations, list) and locations:
            location = clean_location(", ".join(str(x) for x in locations if x))

        path = item.get("positionUrl") or ""
        job_id = item.get("atsJobId") or item.get("displayJobId") or item.get("id")

        jobs.append(
            DiscoveredJob(
                company="",
                external_job_id=str(job_id) if job_id is not None else None,
                title=clean_title(item.get("name")),
                location=location,
                job_url=(
                    f"https://{host}{path}"
                    if path.startswith("/")
                    else (path or None)
                ),
                posted_at=parse_posted_at(
                    item.get("postedTs") or item.get("creationTs")
                ),
                source="eightfold",
            )
        )

    return jobs


class EightfoldSource:
    name = "eightfold"

    def discover(self, token: str) -> list[DiscoveredJob]:
        host, sep, domain = token.partition("|")
        if not sep or not host:
            return []

        jobs: list[DiscoveredJob] = []
        seen: set[str] = set()

        for location in _LOCATIONS:
            for page in range(_PAGES):
                data = get_json(
                    SEARCH.format(host=host),
                    params={
                        "domain": domain,
                        "query": "",
                        "location": location,
                        "start": page * _PAGE_SIZE,
                        "num": _PAGE_SIZE,
                        "sort_by": "timestamp",
                    },
                )
                batch = parse_jobs(data, token)
                if not batch:
                    break

                for job in batch:
                    key = job.external_job_id or job.job_url or job.title
                    if key in seen:
                        continue
                    seen.add(key)
                    jobs.append(job)

                if all(_is_old(job.posted_at) for job in batch):
                    break

        _enrich(jobs, host, domain)
        return jobs


def _is_old(posted_at: datetime | None) -> bool:
    if posted_at is None:
        return True
    return (datetime.utcnow() - posted_at).days > 3


_URL_ID = re.compile(r"/careers/job/(\d+)")


def _enrich(jobs: list[DiscoveredJob], host: str, domain: str) -> None:
    """Fill .description for the newest in-window positions from the
    per-position detail endpoint (one GET each). Best effort. The detail
    endpoint keys off Eightfold's internal id, which is the trailing
    number in positionUrl (not the ATS id we store)."""
    fresh = [j for j in jobs if not _is_old(j.posted_at)][:_ENRICH_MAX]

    for job in fresh:
        match = _URL_ID.search(job.job_url or "")
        if not match:
            continue
        data = get_json(
            DETAIL.format(host=host),
            params={
                "position_id": match.group(1),
                "domain": domain,
                "hl": "en",
            },
        )
        for pos in _positions(data) or (
            [data.get("data")] if isinstance(data, dict) else []
        ):
            if isinstance(pos, dict) and pos.get("jobDescription"):
                job.description = clean_description(pos["jobDescription"])
                break
