"""Goldman Sachs careers (higher.gs.com).

    POST https://api-higher.gs.com/gateway/api/v1/graphql
         query GetRoles - roleSearch { items { roleId jobTitle locations ... } }

Unauthenticated. Per-company adapter, ``token`` unused. The schema has
no posted-date field, so this is a DATELESS source: it pulls the newest
few pages (sorted POSTED_DATE desc) and the not-seen sweep retires them.
"""

from __future__ import annotations

import re

from ..normalize import clean_location, clean_title
from .base import DiscoveredJob, get_json

URL = "https://api-higher.gs.com/gateway/api/v1/graphql"
# The detail page keys off the *numeric* req id only - passing the full
# "166191_GS_MID_CAREER" roleId lands on "Oops, something went wrong".
VIEW = "https://higher.gs.com/roles/{req_id}"

_QUERY = (
    "query GetRoles($s: RoleSearchQueryInput!) { roleSearch(searchQueryInput: $s) "
    "{ totalCount items { roleId jobTitle jobFunction division "
    "locations { city state country primary } } } }"
)
_PAGE_SIZE = 20
_MAX_PAGES = 4  # dateless - only the newest ~80 reqs matter for a 48h view


def _body(page: int) -> dict:
    return {
        "operationName": "GetRoles",
        "variables": {
            "s": {
                "page": {"pageSize": _PAGE_SIZE, "pageNumber": page},
                "sort": {"sortStrategy": "POSTED_DATE", "sortOrder": "DESC"},
                "filters": [],
                "experiences": ["EARLY_CAREER", "PROFESSIONAL"],
                "searchTerm": "",
            }
        },
        "query": _QUERY,
    }


def parse_jobs(payload: object) -> list[DiscoveredJob]:
    data = payload.get("data") if isinstance(payload, dict) else None
    search = data.get("roleSearch") if isinstance(data, dict) else None
    items = search.get("items") if isinstance(search, dict) else None
    if not isinstance(items, list):
        return []

    jobs: list[DiscoveredJob] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        locs = item.get("locations") or []
        loc = None
        if isinstance(locs, list) and locs:
            primary = next(
                (x for x in locs if isinstance(x, dict) and x.get("primary")), locs[0]
            )
            if isinstance(primary, dict):
                loc = clean_location(
                    ", ".join(
                        str(primary[k])
                        for k in ("city", "state", "country")
                        if primary.get(k)
                    )
                )

        role_id = item.get("roleId")
        title = clean_title(item.get("jobTitle"))
        if not role_id or not title:
            continue

        req_match = re.match(r"\d+", str(role_id))
        job_url = (
            VIEW.format(req_id=req_match.group(0)) if req_match else None
        )

        jobs.append(
            DiscoveredJob(
                company="",
                external_job_id=str(role_id),
                title=title,
                location=loc,
                job_url=job_url,
                posted_at=None,  # schema has no date - DATELESS
                source="goldman",
            )
        )

    return jobs


class GoldmanSource:
    name = "goldman"

    def discover(self, token: str = "") -> list[DiscoveredJob]:
        jobs: list[DiscoveredJob] = []
        for page in range(1, _MAX_PAGES + 1):
            data = get_json(URL, json_body=_body(page))
            batch = parse_jobs(data)
            if not batch:
                break
            jobs.extend(batch)
            if len(batch) < _PAGE_SIZE:
                break
        return jobs
