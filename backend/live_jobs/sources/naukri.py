"""Naukri.com source - headless-browser only.

    token = "<Company Name>"     e.g. "Google", "Goldman Sachs"

Naukri has no public API and challenges datacenter IPs hard, so this
adapter renders the company's Bengaluru search-results page with the
same Playwright pool as ``browser`` and scrapes the job cards. If
Chromium isn't installed, or Naukri serves an interstitial instead of
results, it returns [] - like every other flaky feed.

Uniqueness is the upsert key ``(company, external_job_id, source)`` in
``service.upsert_live_job`` - the numeric id at the tail of a Naukri job
URL is stable, so re-runs update the same row instead of duplicating.
It's registered as its own ``source`` ("naukri") so the frontend can
show a dedicated Naukri view.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from ..normalize import clean_location, clean_title
from .base import DiscoveredJob

try:
    from .browser import _render_html
except Exception:  # pragma: no cover - browser deps optional
    _render_html = None  # type: ignore[assignment]

_HOST = "https://www.naukri.com"
_MAX_CARDS = 25

# "3 Days Ago", "Just Now", "Few Hours Ago", "30+ Days Ago", "Today"
_AGE_DAYS = re.compile(r"(\d+)\+?\s*days?\s*ago", re.I)
_AGE_FRESH = re.compile(r"just now|few hours|today|hour", re.I)

# the numeric job id Naukri puts at the end of a job-listing URL
_JOB_ID = re.compile(r"-(\d{6,})(?:\?|$)")


def _slug(company: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", company.lower()).strip("-")
    return s


def search_url(company: str) -> str:
    return f"{_HOST}/{_slug(company)}-jobs-in-bengaluru"


def _parse_age(text: str | None) -> datetime | None:
    if not text:
        return None
    now = datetime.utcnow()
    if _AGE_FRESH.search(text):
        return now
    m = _AGE_DAYS.search(text)
    if m:
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight - timedelta(days=min(int(m.group(1)), 60))
    return None


def parse_jobs(html: str | None, company: str) -> list[DiscoveredJob]:
    if not html:
        return []
    try:
        from bs4 import BeautifulSoup
    except ImportError:  # pragma: no cover
        return []

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(
        "div.srp-jobtuple-wrapper, article.jobTuple, div.job-tuple"
    )

    jobs: list[DiscoveredJob] = []
    seen: set[str] = set()

    for card in cards:
        link = card.select_one("a.title, a.jobTupleHeader, a[href*='job-listings']")
        if link is None or not link.get("href"):
            continue
        href = link["href"].split("?")[0]
        if href in seen:
            continue
        seen.add(href)

        title = clean_title(link.get("title") or link.get_text(" "))
        if not title:
            continue

        loc_el = card.select_one("span.locWdth, span.loc-wrap, .location")
        location = clean_location(loc_el.get_text(" ")) if loc_el else "Bengaluru"

        age_el = card.select_one(
            "span.job-post-day, span.jobTupleFooter span, .job-post-day"
        )
        posted_at = _parse_age(age_el.get_text(" ")) if age_el else None

        desc_el = card.select_one("span.job-desc, .job-description")
        description = desc_el.get_text(" ", strip=True) if desc_el else None

        id_match = _JOB_ID.search(href)
        external_id = id_match.group(1) if id_match else re.sub(r"\W+", "", href)[-24:]

        jobs.append(
            DiscoveredJob(
                company=company,
                external_job_id=external_id or None,
                title=title,
                location=location,
                job_url=href if href.startswith("http") else _HOST + href,
                posted_at=posted_at,
                description=description,
                source="naukri",
            )
        )
        if len(jobs) >= _MAX_CARDS:
            break

    return jobs


class NaukriSource:
    name = "naukri"

    def discover(self, token: str) -> list[DiscoveredJob]:
        if not token or _render_html is None:
            return []
        return parse_jobs(_render_html(search_url(token)), token)
