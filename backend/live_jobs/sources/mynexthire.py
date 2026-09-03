"""MyNextHire ATS careers feeds.

    POST https://{tenant}.mynexthire.com/employer/careers/reqlist/get
         {"source": "careers", "pageNo": 1, "pageSize": 500}

Unauthenticated (the ``source`` field is required or it 417s). Returns
every open requisition in ``reqDetailsBOList``. ``token`` is the tenant
subdomain, e.g. ``"swiggy"`` or ``"sharechat"``. ``approvedOn`` dates
run weeks stale, so this is treated as a DATELESS source.
"""

from __future__ import annotations

from ..normalize import clean_location, clean_title, parse_posted_at
from .base import DiscoveredJob, get_json

URL = "https://{tenant}.mynexthire.com/employer/careers/reqlist/get"
VIEW = "https://{tenant}.mynexthire.com/employer/jobs?src=careers&reqId={req_id}"


def parse_jobs(payload: object, tenant: str = "") -> list[DiscoveredJob]:
    if not isinstance(payload, dict) or not isinstance(
        payload.get("reqDetailsBOList"), list
    ):
        return []

    jobs: list[DiscoveredJob] = []

    for item in payload["reqDetailsBOList"]:
        if not isinstance(item, dict):
            continue

        req_id = item.get("reqId")

        jobs.append(
            DiscoveredJob(
                company="",
                external_job_id=str(req_id) if req_id else None,
                title=clean_title(item.get("reqTitle") or item.get("designation")),
                location=clean_location(item.get("location")),
                job_url=(
                    VIEW.format(tenant=tenant, req_id=req_id)
                    if req_id and tenant
                    else None
                ),
                posted_at=parse_posted_at(item.get("approvedOn")),
                source="mynexthire",
            )
        )

    return jobs


class MyNextHireSource:
    name = "mynexthire"

    def discover(self, token: str = "swiggy") -> list[DiscoveredJob]:
        tenant = (token or "swiggy").strip().strip("/")
        if not tenant:
            return []
        data = get_json(
            URL.format(tenant=tenant),
            json_body={"source": "careers", "pageNo": 1, "pageSize": 500},
        )
        return parse_jobs(data, tenant)
