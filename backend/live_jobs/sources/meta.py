"""Meta (Facebook) careers - metacareers.com Relay/GraphQL.

    POST https://www.metacareers.com/graphql
        doc_id    = <CareersJobSearchResultsV2DataQuery persisted-query id>
        lsd       = <token scraped from the /jobs/ page>
        variables = {"search_input": {... "offices": [...] ...},
                     "isLoggedIn": false}

Meta actively fights scrapers, so this adapter:

- loads ``metacareers.com`` then ``/jobs/`` to pick up a ``datr`` cookie
  and a fresh ``lsd`` token (the token's surrounding markup varies between
  loads, so a few patterns are tried);
- sends a persisted-query ``doc_id`` that Meta rotates on roughly every
  weekly deploy. A stale id comes back as HTTP 200 with an
  ``{"errors": [...]}`` body - ``parse_jobs`` then finds no job node and
  returns [], and the not-seen sweep retires Meta rows until ``DOC_ID``
  is refreshed (grep metacareers.com's JS bundles for the friendly name).

The V2 query returns only the ~20 newest reqs and ignores paging, and
the feed carries no post date - Meta is a DATELESS, single-metro source.
``token`` is unused (per-company adapter).
"""

from __future__ import annotations

import json
import re
import time

import requests

from ..normalize import clean_location, clean_title
from .base import DiscoveredJob

HOME = "https://www.metacareers.com/"
JOBS_PAGE = "https://www.metacareers.com/jobs/"
GRAPHQL = "https://www.metacareers.com/graphql"
VIEW = "https://www.metacareers.com/jobs/{job_id}/"

# Persisted-query id for CareersJobSearchResultsV2DataQuery. Meta rotates
# this ~weekly; refresh by grepping metacareers.com's JS bundles for the
# friendly name. A stale id yields an {"errors": [...]} body -> [].
DOC_ID = "27129360303422352"
FRIENDLY = "CareersJobSearchResultsV2DataQuery"

# Meta's office names for the metros this tracker follows. The V2 query
# caps results at ~20 with no paging, so the two offices share those
# slots - widen further only alongside a paginating query.
OFFICES = ["Bangalore, India", "Hyderabad, India"]

_TIMEOUT = (5, 20)
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
)
_LSD_PATTERNS = (
    r'"LSD",\[\],\{"token":"([^"]+)"',
    r'\["LSD",\[\],\{"token":"([^"]+)"\}',
    r'name="lsd"\s+value="([^"]+)"',
    r'"lsd":"([^"]+)"',
)


def _bootstrap() -> tuple[requests.Session, str] | None:
    """Load the careers site for a ``datr`` cookie + a fresh ``lsd``.

    Both the ``datr``-setting request and the ``lsd`` markup are flaky
    (and 4xx outright once Meta has flagged the caller's IP), so retry a
    couple of times before giving up.
    """
    for attempt in range(3):
        if attempt:
            time.sleep(2)

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": _BROWSER_UA,
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

        try:
            session.get(HOME, timeout=_TIMEOUT)
            page = session.get(JOBS_PAGE, timeout=_TIMEOUT)
        except requests.RequestException:
            continue

        if page.status_code != 200:
            continue

        for pattern in _LSD_PATTERNS:
            match = re.search(pattern, page.text)
            if match:
                return session, match.group(1)

    return None


def _search_input() -> dict:
    return {
        "q": None,
        "divisions": [],
        "offices": OFFICES,
        "roles": [],
        "leadership_levels": [],
        "saved_jobs": [],
        "saved_searches": [],
        "sub_teams": [],
        "teams": [],
        "is_leadership": False,
        "is_remote_only": False,
        "sort_by_new": True,
        "results_per_page": None,
    }


def _fetch(session: requests.Session, lsd: str) -> object | None:
    variables = {
        "search_input": _search_input(),
        "viewasUserID": None,
        "isLoggedIn": False,
    }
    body = {
        "lsd": lsd,
        "doc_id": DOC_ID,
        "variables": json.dumps(variables),
        "fb_api_req_friendly_name": FRIENDLY,
        "fb_api_caller_class": "RelayModern",
        "server_timestamps": "true",
        "__a": "1",
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-FB-LSD": lsd,
        "X-FB-Friendly-Name": FRIENDLY,
        "X-ASBD-ID": "359341",
        "Origin": "https://www.metacareers.com",
        "Referer": "https://www.metacareers.com/jobsearch/",
    }

    try:
        response = session.post(
            GRAPHQL, data=body, headers=headers, timeout=_TIMEOUT
        )
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    try:
        return response.json()
    except ValueError:
        return None


def parse_jobs(payload: object) -> list[DiscoveredJob]:
    node = payload.get("data") if isinstance(payload, dict) else None
    node = (
        node.get("job_search_with_featured_jobs_v2")
        if isinstance(node, dict)
        else None
    )
    if not isinstance(node, dict) or not isinstance(node.get("all_jobs"), list):
        return []

    jobs: list[DiscoveredJob] = []

    for item in node["all_jobs"]:
        if not isinstance(item, dict):
            continue

        job_id = item.get("id")
        if not job_id:
            continue

        locations = item.get("locations")
        location = (
            clean_location(
                "; ".join(x for x in locations if isinstance(x, str))
            )
            if isinstance(locations, list)
            else None
        )

        jobs.append(
            DiscoveredJob(
                company="Meta",
                external_job_id=str(job_id),
                title=clean_title(item.get("title")),
                location=location,
                job_url=VIEW.format(job_id=job_id),
                posted_at=None,  # feed carries no post date - DATELESS
                source="meta",
            )
        )

    return jobs


class MetaSource:
    name = "meta"

    def discover(self, token: str = "") -> list[DiscoveredJob]:
        boot = _bootstrap()
        if boot is None:
            return []

        session, lsd = boot
        return parse_jobs(_fetch(session, lsd))
