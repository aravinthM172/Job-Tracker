"""Swiggy careers - MyNextHire ATS.

    POST https://swiggy.mynexthire.com/employer/careers/reqlist/get
         {"source": "careers", "pageNo": 1, "pageSize": 500}

Unauthenticated (needs the ``source`` field or it 417s). Returns every
open requisition in ``reqDetailsBOList``; ``approvedOn`` is the post
date. Per-company adapter - ``token`` unused.
"""

from __future__ import annotations

from ..normalize import clean_location, clean_title, parse_posted_at
from .base import DiscoveredJob, get_json

URL = "https://swiggy.mynexthire.com/employer/careers/reqlist/get"
VIEW = "https://careers.swiggy.com/#/careers/{req_id}"


def parse_jobs(payload: object) -> list[DiscoveredJob]:
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
                company="Swiggy",
                external_job_id=str(req_id) if req_id else None,
                title=clean_title(item.get("reqTitle") or item.get("designation")),
                location=clean_location(item.get("location")),
                job_url=(
                    VIEW.format(req_id=req_id)
                    if req_id
                    else "https://careers.swiggy.com/"
                ),
                posted_at=parse_posted_at(item.get("approvedOn")),
                source="swiggy",
            )
        )

    return jobs


class SwiggySource:
    name = "swiggy"

    def discover(self, token: str = "") -> list[DiscoveredJob]:
        data = get_json(
            URL,
            json_body={"source": "careers", "pageNo": 1, "pageSize": 500},
        )
        return parse_jobs(data)
