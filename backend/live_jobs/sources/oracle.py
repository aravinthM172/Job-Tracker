"""Oracle Cloud Recruiting (Candidate Experience) public feed.

    GET https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions
        ?onlyData=true&expand=requisitionList
        &finder=findReqs;siteNumber={site},limit=N,offset=O,sortBy=POSTING_DATES_DESC

Unauthenticated. ``token`` is ``"host|site"`` e.g.
``"ejgk.fa.em2.oraclecloud.com|CX_3"``. Results are newest-first, so
paging stops once a page is entirely outside the window.
"""

from __future__ import annotations

from datetime import datetime

from ..normalize import clean_location, clean_title, parse_posted_at
from .base import DiscoveredJob, get_json

API = (
    "https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    "?onlyData=true&expand=requisitionList"
    "&finder=findReqs;siteNumber={site},limit={limit},offset={offset}"
    ",sortBy=POSTING_DATES_DESC"
)
VIEW = "https://{host}/hcmUI/CandidateExperience/en/sites/{site}/job/{job_id}"

_PAGES = 3
_PAGE_SIZE = 25


def _requisitions(payload: object) -> list:
    if not isinstance(payload, dict):
        return []
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        return []
    wrapper = items[0]
    reqs = wrapper.get("requisitionList") if isinstance(wrapper, dict) else None
    return reqs if isinstance(reqs, list) else []


def parse_jobs(payload: object, token: str = "") -> list[DiscoveredJob]:
    host, _, site = token.partition("|")

    jobs: list[DiscoveredJob] = []

    for item in _requisitions(payload):
        if not isinstance(item, dict):
            continue

        job_id = item.get("Id")

        jobs.append(
            DiscoveredJob(
                company="",
                external_job_id=str(job_id) if job_id else None,
                title=clean_title(item.get("Title")),
                location=clean_location(item.get("PrimaryLocation")),
                job_url=(
                    VIEW.format(host=host, site=site, job_id=job_id)
                    if job_id and host
                    else None
                ),
                posted_at=parse_posted_at(item.get("PostedDate")),
                source="oracle",
            )
        )

    return jobs


class OracleSource:
    name = "oracle"

    def discover(self, token: str) -> list[DiscoveredJob]:
        host, sep, site = token.partition("|")
        if not sep:
            return []

        jobs: list[DiscoveredJob] = []

        for page in range(_PAGES):
            data = get_json(
                API.format(
                    host=host,
                    site=site,
                    limit=_PAGE_SIZE,
                    offset=page * _PAGE_SIZE,
                )
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
