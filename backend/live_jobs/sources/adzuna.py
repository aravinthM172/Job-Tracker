"""Adzuna job-aggregator API - a single broad query per cycle that back-
fills companies with no fetchable first-party feed.

    GET https://api.adzuna.com/v1/api/jobs/in/search/{page}
        ?app_id=...&app_key=...&where=Bengaluru&distance=40
        &sort_by=date&max_days_old=4&results_per_page=50

Needs a free key (https://developer.adzuna.com): env ``ADZUNA_APP_ID``
and ``ADZUNA_APP_KEY``. Without them the adapter is a no-op. Rather than
one call per company (which would blow the 250/day free quota), it pulls
the newest Bengaluru postings and keeps only those whose
``company.display_name`` matches a name in ``ADZUNA_COMPANIES``
(defaults to ``live_jobs.companies.COMPANIES``). ``token`` is unused -
the job's own company is trusted, so discovery must not overwrite it.
"""

from __future__ import annotations

import os

from ..companies import COMPANIES
from ..normalize import clean_location, clean_title, normalize_company, parse_posted_at
from .base import DiscoveredJob, get_json

API = "https://api.adzuna.com/v1/api/jobs/in/search/{page}"
_PAGES = 3


def _targets() -> dict[str, str]:
    """Companies to back-fill: the target universe MINUS anything that
    already has a first-party feed (so Adzuna never double-lists). Override
    the whole set with ``ADZUNA_COMPANIES`` (comma-separated)."""
    raw = os.getenv("ADZUNA_COMPANIES")
    if raw:
        names = [n.strip() for n in raw.split(",") if n.strip()]
    else:
        from ..company_sources import COMPANY_SOURCES

        covered = {
            normalize_company(c)
            for c, feeds in COMPANY_SOURCES.items()
            if any(s != "adzuna" for s, _ in feeds)
        }
        names = [c for c in COMPANIES if normalize_company(c) not in covered]

    return {normalize_company(n): n for n in names}


def _match(display: str | None, targets: dict[str, str]) -> str | None:
    if not display:
        return None
    key = normalize_company(display)
    if key in targets:
        return targets[key]
    for tkey, name in targets.items():
        if tkey and (tkey in key or key in tkey):
            return name
    return None


def parse_jobs(payload: object, targets: dict[str, str] | None = None) -> list[DiscoveredJob]:
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        return []

    targets = targets if targets is not None else _targets()
    jobs: list[DiscoveredJob] = []

    for item in payload["results"]:
        if not isinstance(item, dict):
            continue

        company = _match((item.get("company") or {}).get("display_name"), targets)
        if not company:
            continue

        location = item.get("location") or {}
        job_id = item.get("id")

        jobs.append(
            DiscoveredJob(
                company=company,
                external_job_id=str(job_id) if job_id else None,
                title=clean_title(item.get("title")),
                location=clean_location(location.get("display_name")),
                job_url=item.get("redirect_url"),
                posted_at=parse_posted_at(item.get("created")),
                description=item.get("description"),
                source="adzuna",
            )
        )

    return jobs


class AdzunaSource:
    name = "adzuna"
    # discovery must keep each job's own .company, not the feed's key
    keeps_company = True

    def discover(self, token: str = "") -> list[DiscoveredJob]:
        app_id = os.getenv("ADZUNA_APP_ID")
        app_key = os.getenv("ADZUNA_APP_KEY")
        if not app_id or not app_key:
            return []

        targets = _targets()
        jobs: list[DiscoveredJob] = []

        for page in range(1, _PAGES + 1):
            data = get_json(
                API.format(page=page),
                params={
                    "app_id": app_id,
                    "app_key": app_key,
                    "where": "Bengaluru",
                    "distance": 40,
                    "sort_by": "date",
                    "max_days_old": 4,
                    "results_per_page": 50,
                },
            )
            batch = parse_jobs(data, targets)
            page_count = (
                len(data.get("results", [])) if isinstance(data, dict) else 0
            )
            jobs.extend(batch)
            if page_count < 50:
                break

        return jobs
