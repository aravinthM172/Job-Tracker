"""Radancy / TalentBrew careers sites ("search-jobs/results" AJAX).

    GET {base}/search-jobs/results
        ?SortCriteria=5&SortDirection=1&RecordsPerPage=100&CurrentPage=N&...

Unauthenticated. Returns JSON whose ``results`` field is an HTML
fragment - one ``<li>`` per posting - which this adapter scrapes.
``token`` is the site base URL (e.g. ``"https://careers.synopsys.com"``).

The feed has no working server-side country filter, so the adapter
pulls the newest few hundred reqs (``SortCriteria=5`` = date, newest
first) and lets the discovery location filter narrow to the metro. Some
sites print a ``MM/DD/YYYY`` posted date per card; on sites that don't
(e.g. Arm) only the first ``_MAX_UNDATED`` newest reqs are kept, with a
synthetic recent timestamp, so a dateless board can't flood the
dashboard.
"""

from __future__ import annotations

import html as _html
import re
from datetime import datetime, timedelta

import json as _json

from ..normalize import (
    clean_description,
    clean_location,
    clean_title,
    parse_posted_at,
)
from .base import DiscoveredJob, get_json, get_text

_ENRICH_MAX = 12
_LD_BLOCK = re.compile(
    r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', re.S | re.I
)

_PARAMS = {
    "ActiveFacetID": "0",
    "CurrentPage": "1",
    "RecordsPerPage": "100",
    "Distance": "50",
    "RadiusUnitType": "0",
    "Keywords": "",
    "ShowRadius": "False",
    "IsPagination": "False",
    "SearchResultsModuleName": "Search Results",
    "SearchFiltersModuleName": "Search Filters",
    "SortCriteria": "5",  # posted date
    "SortDirection": "1",  # newest first
    "SearchType": "5",
}
_PAGES = 3
# On sites with no per-card date, keep only this many newest reqs.
_MAX_UNDATED = 25

_BLOCK = re.compile(r"<li\b[^>]*>.*?</li>", re.S | re.I)
_JOB_ID = re.compile(r'data-job-id="([^"]+)"')
_HREF = re.compile(r'href="(/job/[^"]+)"')
_H2 = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.S | re.I)
_ANCHOR = re.compile(r'data-job-id="[^"]*"[^>]*>(.*?)</a>', re.S | re.I)
_LOCATION = re.compile(
    r'class="[^"]*\blocation\b[^"]*"[^>]*>(?:\s*<img[^>]*>)?\s*([^<]+)', re.I
)
_DATE = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{4})\b")
_TAG = re.compile(r"<[^>]+>")


def _text(fragment: str) -> str:
    return clean_title(_html.unescape(_TAG.sub(" ", fragment)))


def parse_jobs(payload: object, token: str = ""):
    if isinstance(payload, dict):
        html = payload.get("results")
    elif isinstance(payload, str):
        html = payload
    else:
        html = None
    if not isinstance(html, str) or not html:
        return []

    base = token.rstrip("/")
    jobs: list[DiscoveredJob] = []

    for block in _BLOCK.findall(html):
        href = _HREF.search(block)
        if not href:
            continue
        path = href.group(1)

        job_id_match = _JOB_ID.search(block)
        job_id = (
            job_id_match.group(1)
            if job_id_match
            else path.rstrip("/").rsplit("/", 1)[-1]
        )

        title_match = _H2.search(block) or _ANCHOR.search(block)
        title = _text(title_match.group(1)) if title_match else ""

        loc_match = _LOCATION.search(block)
        date_match = _DATE.search(block)

        jobs.append(
            DiscoveredJob(
                company="",
                external_job_id=str(job_id) if job_id else None,
                title=title,
                location=(
                    clean_location(_html.unescape(loc_match.group(1)))
                    if loc_match
                    else None
                ),
                job_url=(base + path) if base else None,
                posted_at=(
                    parse_posted_at(date_match.group(1)) if date_match else None
                ),
                source="radancy",
            )
        )

    return jobs


class RadancySource:
    name = "radancy"

    def discover(self, token: str) -> list[DiscoveredJob]:
        # token is the site base URL, optionally "base||k=v&k2=v2" to pin
        # extra search params (e.g. an org id or a location facet).
        base_part, _, extra = token.partition("||")
        base = base_part.rstrip("/")
        if not base.startswith("http"):
            return []

        pinned = dict(
            p.split("=", 1) for p in extra.split("&") if "=" in p
        )

        jobs: list[DiscoveredJob] = []

        for page in range(1, _PAGES + 1):
            data = get_json(
                f"{base}/search-jobs/results",
                params={**_PARAMS, **pinned, "CurrentPage": str(page)},
            )
            batch = parse_jobs(data, base)
            if not batch:
                break

            jobs.extend(batch)

        jobs = _fill_undated(jobs)
        _enrich(jobs)
        return jobs


def _enrich(jobs: list[DiscoveredJob]) -> None:
    """Lift JobPosting.description from each job page's JSON-LD. Best effort."""
    for job in jobs[:_ENRICH_MAX]:
        if not job.job_url:
            continue
        html = get_text(job.job_url)
        if not html:
            continue
        for block in _LD_BLOCK.findall(html):
            try:
                data = _json.loads(block.strip())
            except (ValueError, TypeError):
                continue
            for entry in data if isinstance(data, list) else [data]:
                if (
                    isinstance(entry, dict)
                    and entry.get("@type") == "JobPosting"
                    and entry.get("description")
                ):
                    job.description = clean_description(entry["description"])
                    break
            if job.description:
                break


def _fill_undated(jobs: list[DiscoveredJob]) -> list[DiscoveredJob]:
    """Feed is newest-first. Give the first few reqs with no card date a
    synthetic recent timestamp; drop the rest so a dateless board can't
    swamp the 48h dashboard."""
    now = datetime.utcnow()
    out: list[DiscoveredJob] = []
    undated = 0

    for job in jobs:
        if job.posted_at is not None:
            out.append(job)
            continue
        if undated >= _MAX_UNDATED:
            continue
        job.posted_at = now - timedelta(hours=1, minutes=20 * undated)
        undated += 1
        out.append(job)

    return out
