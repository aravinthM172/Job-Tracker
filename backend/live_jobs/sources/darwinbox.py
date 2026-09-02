"""Darwinbox-hosted careers pages ({tenant}.darwinbox.in).

    GET  https://{tenant}.darwinbox.in/ms/candidatev2/main/careers/home   (cookie)
    POST https://{tenant}.darwinbox.in/ms/candidateapi/job/alljobs?companyId={cid}
         {}

Unauthenticated - the feed the Darwinbox careers SPA calls, but the POST
needs a Cloudflare ``__cf_bm`` cookie picked up from a prior page GET.
``token`` is ``"{tenant}|{companyId}"`` (companyId is usually "main").
``posted_on`` is epoch seconds. Common for Indian companies.
"""

from __future__ import annotations

import requests

from ..normalize import clean_location, clean_title, parse_posted_at
from .base import DiscoveredJob

HOME = "https://{tenant}.darwinbox.in/ms/candidatev2/main/careers/home"
API = "https://{tenant}.darwinbox.in/ms/candidateapi/job/alljobs"
VIEW = "https://{tenant}.darwinbox.in/ms/candidatev2/main/careers/job/{job_id}"

_TIMEOUT = (5, 20)
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
)


def _fetch(tenant: str, company_id: str) -> object | None:
    session = requests.Session()
    session.headers.update({"User-Agent": _UA, "Accept": "application/json"})
    try:
        session.get(HOME.format(tenant=tenant), timeout=_TIMEOUT)
        response = session.post(
            API.format(tenant=tenant),
            params={"companyId": company_id},
            json={},
            headers={
                "Content-Type": "application/json",
                "Origin": f"https://{tenant}.darwinbox.in",
                "Referer": (
                    f"https://{tenant}.darwinbox.in"
                    "/ms/candidatev2/main/careers/allJobs"
                ),
            },
            timeout=_TIMEOUT,
        )
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None
    try:
        return response.json()
    except ValueError:
        return None


def parse_jobs(payload: object, token: str = "") -> list[DiscoveredJob]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return []

    tenant = token.split("|", 1)[0]

    jobs: list[DiscoveredJob] = []

    for item in payload["data"]:
        if not isinstance(item, dict):
            continue

        job_id = item.get("id")
        where = item.get("locations") or item.get("tool_tip_locations")
        if isinstance(where, str) and where.lower() == "multiple locations":
            where = item.get("country")

        jobs.append(
            DiscoveredJob(
                company="",
                external_job_id=str(job_id) if job_id else None,
                title=clean_title(
                    item.get("title") or item.get("designation_title_name")
                ),
                location=clean_location(where if isinstance(where, str) else None),
                job_url=(
                    VIEW.format(tenant=tenant, job_id=job_id)
                    if job_id and tenant
                    else None
                ),
                posted_at=parse_posted_at(
                    item.get("posted_on") or item.get("created_on")
                ),
                source="darwinbox",
            )
        )

    return jobs


class DarwinboxSource:
    name = "darwinbox"

    def discover(self, token: str) -> list[DiscoveredJob]:
        tenant, _, company_id = token.partition("|")
        if not company_id:
            return []

        return parse_jobs(_fetch(tenant, company_id), token)
