"""Live Jobs discovery pipeline.

For every company in ``COMPANY_SOURCES`` we hit that company's public
careers feed (in parallel), normalise each posting, drop anything older
than the 48h window, and upsert the rest. Returns a dict of counts so
the caller can log a one-line summary.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session

from .company_sources import COMPANY_SOURCES
from .normalize import (
    clean_location,
    clean_title,
    fallback_external_id,
    parse_posted_at,
)
from .service import find_live_job, live_job_cutoff, upsert_live_job
from .sources import SOURCES

_MAX_WORKERS = 12


def _fetch_company(company: str, feeds: list[tuple[str, str]]) -> list:
    """Run every feed configured for one company. Never raises."""
    jobs = []

    for source_name, token in feeds:
        source = SOURCES.get(source_name)
        if source is None:
            continue

        try:
            found = source.discover(token)
        except Exception:
            found = []

        for job in found:
            job.company = company
            jobs.append(job)

    return jobs


def discover_all_companies(db: Session) -> dict[str, int]:
    counts = {
        "companies": len(COMPANY_SOURCES),
        "fetched": 0,
        "skipped_old": 0,
        "skipped_invalid": 0,
        "new": 0,
        "updated": 0,
    }

    cutoff = live_job_cutoff()

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        company_batches = list(
            pool.map(lambda item: _fetch_company(*item), COMPANY_SOURCES.items())
        )

    for batch in company_batches:
        for job in batch:
            counts["fetched"] += 1

            title = clean_title(job.title)
            posted_at = parse_posted_at(job.posted_at)

            if not title or posted_at is None:
                counts["skipped_invalid"] += 1
                continue

            if posted_at < cutoff:
                counts["skipped_old"] += 1
                continue

            location = clean_location(job.location)
            external_id = job.external_job_id or fallback_external_id(
                job.company, title, location, job.job_url
            )

            is_new = (
                find_live_job(db, job.company, external_id, job.source) is None
            )

            upsert_live_job(
                db,
                company=job.company,
                external_job_id=external_id,
                title=title,
                location=location,
                job_url=job.job_url,
                source=job.source,
                posted_at=posted_at,
                description=job.description,
            )

            counts["new" if is_new else "updated"] += 1

    return counts


__all__ = ["discover_all_companies"]
