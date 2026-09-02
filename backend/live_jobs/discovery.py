"""Live Jobs discovery pipeline.

Runs inside the existing 5-minute sync. To stay light on a shared box:

- cheap single-request ATS feeds (greenhouse / lever / ashby) run every
  cycle; heavy feeds (workday / amazon) run every 3rd cycle (~15 min);
- companies are fetched in parallel, and each company's postings are
  ingested and freed as they arrive (no big in-memory accumulation);
- a wall-clock budget stops the run early - anything not reached is
  picked up next cycle.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy.orm import Session

from .companies import is_target_company
from .company_sources import COMPANY_SOURCES
from .config import location_filter, location_matches
from .normalize import (
    clean_location,
    clean_title,
    fallback_external_id,
    parse_posted_at,
)
from datetime import datetime, timedelta

from .service import find_live_job, live_job_cutoff, upsert_live_job
from .sources import DATELESS_SOURCES, GUARDED_SOURCES, HEAVY_SOURCES, SOURCES

_MAX_WORKERS = 10
_BUDGET_SECONDS = 150
_HEAVY_EVERY = 4  # cycles (~20 min for workday / amazon / oracle)
_GUARDED_EVERY = 6  # cycles (~30 min for google / meta - see GUARDED_SOURCES)

_cycle = 0


def _fetch_company(company: str, feeds: list[tuple[str, str]]) -> list:
    """Run every configured feed for one company. Never raises."""
    jobs = []

    for source_name, token in feeds:
        source = SOURCES.get(source_name)
        if source is None:
            continue

        try:
            found = source.discover(token)
        except Exception:
            found = []

        # aggregator sources (adzuna) attribute each job to its own
        # company; everything else is keyed by the company we asked for
        keeps_company = getattr(source, "keeps_company", False)
        for job in found:
            if not keeps_company:
                job.company = company
            elif not is_target_company(job.company):
                continue  # aggregator hit for a company outside companies.py
            if job.company:
                jobs.append(job)

    return jobs


def _ingest(db: Session, batch: list, cutoff, locations, counts: dict) -> None:
    for job in batch:
        counts["fetched"] += 1

        title = clean_title(job.title)
        posted_at = parse_posted_at(job.posted_at)
        dateless = job.source in DATELESS_SOURCES

        if not title or (posted_at is None and not dateless):
            counts["skipped_invalid"] += 1
            continue

        if dateless:
            # no trustworthy post date - keep every open req in-window
            # and let the not-seen sweep retire it later
            if posted_at is None or posted_at < cutoff:
                posted_at = datetime.utcnow() - timedelta(hours=12)
        elif posted_at < cutoff:
            counts["skipped_old"] += 1
            continue

        location = clean_location(job.location)

        if not location_matches(location, locations):
            counts["skipped_location"] += 1
            continue

        external_id = job.external_job_id or fallback_external_id(
            job.company, title, location, job.job_url
        )

        is_new = find_live_job(db, job.company, external_id, job.source) is None

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
            commit=False,
        )

        counts["new" if is_new else "updated"] += 1


def _select_feeds(
    feeds: list[tuple[str, str]], run_heavy: bool, run_guarded: bool
):
    selected = []
    for source_name, token in feeds:
        if source_name in GUARDED_SOURCES and not run_guarded:
            continue
        if source_name in HEAVY_SOURCES and not run_heavy:
            continue
        selected.append((source_name, token))
    return selected


def discover_all_companies(db: Session) -> dict[str, int]:
    global _cycle
    _cycle += 1
    run_heavy = _cycle % _HEAVY_EVERY == 1
    run_guarded = _cycle % _GUARDED_EVERY == 1

    counts = {
        "cycle": _cycle,
        "heavy": int(run_heavy),
        "guarded": int(run_guarded),
        "companies": 0,
        "fetched": 0,
        "skipped_off_list": 0,
        "skipped_old": 0,
        "skipped_invalid": 0,
        "skipped_location": 0,
        "new": 0,
        "updated": 0,
        "timed_out": 0,
    }

    work = []
    for company, feeds in COMPANY_SOURCES.items():
        # companies.py is the allowlist - skip ATS slugs for anything
        # outside it (aggregator hits are re-checked per job in _fetch_company)
        if not is_target_company(company):
            counts["skipped_off_list"] += 1
            continue
        selected = _select_feeds(feeds, run_heavy, run_guarded)
        if selected:
            work.append((company, selected))

    counts["companies"] = len(work)
    cutoff = live_job_cutoff()
    locations = location_filter()
    deadline = time.monotonic() + _BUDGET_SECONDS

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        futures = {
            pool.submit(_fetch_company, company, feeds): company
            for company, feeds in work
        }

        for future in as_completed(futures):
            if time.monotonic() > deadline:
                counts["timed_out"] = 1
                for pending in futures:
                    pending.cancel()
                break

            _ingest(db, future.result(), cutoff, locations, counts)
            db.commit()  # one commit per company, not per posting

    return counts


__all__ = ["discover_all_companies"]
