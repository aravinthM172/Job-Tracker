"""SAP SuccessFactors "Career Site Builder" sites.

    GET {search_url}&startrow=0        (server-rendered)

The CSB search page renders a ``<tr class="data-row">`` per posting -
``a.jobTitle-link`` for the title/href, ``span.jobLocation`` for the
location. ``token`` is the search URL, already filtered to the target
country (``&locationsearch=India``). Cards carry no posted date, so this
is a DATELESS source, capped at the first ~25 rows and relying on the
not-seen sweep.
"""

from __future__ import annotations

import json
import re

import requests

from ..normalize import clean_description, clean_location, clean_title
from .base import DiscoveredJob

_TIMEOUT = (5, 20)
_ENRICH_MAX = 12
_JSONLD = re.compile(
    r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
)

_PAGES = 2
_PAGE_SIZE = 25
_MAX = 20
_SORT = "sortColumn=referencedate&sortDirection=desc"


def _base(url: str) -> str:
    m = re.match(r"https?://[^/]+", url)
    return m.group(0) if m else ""


def parse_jobs(html: str, token: str = "") -> list[DiscoveredJob]:
    if not isinstance(html, str) or "data-row" not in html:
        return []

    try:
        from bs4 import BeautifulSoup
    except ImportError:  # pragma: no cover
        return []

    soup = BeautifulSoup(html, "html.parser")
    base = _base(token)
    jobs: list[DiscoveredJob] = []

    for row in soup.select("tr.data-row"):
        anchor = row.select_one("a.jobTitle-link") or row.find("a", href=True)
        if anchor is None:
            continue
        title = clean_title(anchor.get_text(" "))
        href = anchor.get("href") or ""
        if not title or not href:
            continue

        loc_el = row.select_one("td.colLocation .jobLocation") or row.select_one(
            ".jobLocation"
        )
        location = (
            clean_location(loc_el.get_text(" ")) if loc_el is not None else None
        )

        job_id = re.search(r"/(\d{6,})/?$", href)
        jobs.append(
            DiscoveredJob(
                company="",
                external_job_id=(
                    job_id.group(1) if job_id else re.sub(r"\W+", "", href)[-20:]
                ),
                title=title,
                location=location,
                job_url=href if href.startswith("http") else base + href,
                posted_at=None,  # CSB rows carry no post date - DATELESS
                source="successfactors",
            )
        )

    return jobs


class SuccessFactorsSource:
    name = "successfactors"

    def discover(self, token: str) -> list[DiscoveredJob]:
        if not token.startswith("http"):
            return []

        sep = "&" if "?" in token else "?"
        url = token if "sortColumn=" in token else f"{token}{sep}{_SORT}"
        jobs: list[DiscoveredJob] = []

        for page in range(_PAGES):
            batch = parse_jobs(
                _raw(f"{url}&startrow={page * _PAGE_SIZE}"), token
            )
            if not batch:
                break
            jobs.extend(batch)
            if len(jobs) >= _MAX:
                break

        jobs = jobs[:_MAX]
        _enrich(jobs)
        return jobs


def _page_description(html: str) -> str | None:
    """Lift the ad body from a CSB job page - JSON-LD if present, else the
    ``span.jobdescription`` block the CSB template renders."""
    for block in _JSONLD.findall(html or ""):
        try:
            data = json.loads(block.strip())
        except (ValueError, TypeError):
            continue
        for entry in data if isinstance(data, list) else [data]:
            if (
                isinstance(entry, dict)
                and entry.get("@type") == "JobPosting"
                and entry.get("description")
            ):
                return str(entry["description"])

    try:
        from bs4 import BeautifulSoup
    except ImportError:  # pragma: no cover
        return None

    soup = BeautifulSoup(html or "", "html.parser")
    node = soup.select_one("span.jobdescription") or soup.select_one(
        '[data-bind-propertyid="description"]'
    )
    return node.get_text(" ") if node is not None else None


def _enrich(jobs: list[DiscoveredJob]) -> None:
    """Fetch each job page and lift its description. Best effort."""
    for job in jobs[:_ENRICH_MAX]:
        if not job.job_url:
            continue
        html = _raw(job.job_url)
        if html:
            job.description = clean_description(_page_description(html))


def _raw(url: str) -> str | None:
    try:
        r = requests.get(url, headers={"User-Agent": _UA}, timeout=_TIMEOUT)
    except requests.RequestException:
        return None
    return r.text if r.status_code == 200 else None
