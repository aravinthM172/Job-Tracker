"""Live Jobs persistence + status logic.

The 48h window is enforced in two places on purpose:
- discovery drops old postings before they are ever written;
- the read queries here also filter, so a job that ages out while stored
  disappears from the dashboard without needing a sweep to run first.
``close_old_jobs`` is the sweep that additionally flips ``is_active`` /
``status`` so the stored row stays truthful.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session

from .companies import is_target_company
from .models import LiveJob

LOOKBACK_HOURS = 48

# How long a re-posted job keeps the REPOSTED badge before it settles
# back to LIVE (the is_reposted flag / repost_count stay for the "seen
# N times" annotation).
REPOST_BADGE_HOURS = 48

# Closed rows older than this are deleted outright - keeps the table
# small on a space-constrained box (a job seeker never needs week-old
# expired postings).
PURGE_AFTER_DAYS = 7

# An active job not seen in any discovery run for this long has dropped
# off its source feed - close it. (Heavy feeds refresh ~every 20 min, so
# 36h is many missed cycles.)
NOT_SEEN_CLOSE_HOURS = 36


def utcnow() -> datetime:
    return datetime.utcnow()


def live_job_cutoff() -> datetime:
    return utcnow() - timedelta(hours=LOOKBACK_HOURS)


def calculate_status(job: LiveJob) -> str:
    if not job.is_active:
        return "CLOSED"

    if (
        job.is_reposted
        and job.reposted_at is not None
        and utcnow() - job.reposted_at < timedelta(hours=REPOST_BADGE_HOURS)
    ):
        return "REPOSTED"

    return "NEW" if job.first_seen_at == job.last_seen_at else "LIVE"


def find_live_job(
    db: Session,
    company: str,
    external_job_id: str,
    source: str,
) -> LiveJob | None:
    return db.scalar(
        select(LiveJob).where(
            LiveJob.company == company,
            LiveJob.external_job_id == external_job_id,
            LiveJob.source == source,
        )
    )


def upsert_live_job(
    db: Session,
    *,
    company: str,
    external_job_id: str,
    title: str,
    location: str | None = None,
    job_url: str | None = None,
    source: str = "unknown",
    posted_at: datetime | None = None,
    description: str | None = None,
    commit: bool = True,
) -> LiveJob:
    """Insert or update one posting. ``commit=False`` only flushes, so a
    caller processing a batch can commit once at the end."""
    now = utcnow()
    existing = find_live_job(db, company, external_job_id, source)

    def _persist(row: LiveJob) -> LiveJob:
        db.add(row)
        if commit:
            db.commit()
            db.refresh(row)
        else:
            db.flush()
        return row

    if existing is not None:
        was_inactive = not existing.is_active

        existing.last_seen_at = now
        existing.updated_at = now
        existing.is_active = True

        if title:
            existing.title = title
        if location:
            existing.location = location
        if job_url:
            existing.job_url = job_url
        if description:
            existing.description = description
        if posted_at:
            existing.posted_at = posted_at

        if was_inactive:
            existing.is_reposted = True
            existing.repost_count += 1
            existing.reposted_at = now

        existing.status = calculate_status(existing)
        return _persist(existing)

    job = LiveJob(
        company=company,
        external_job_id=external_job_id,
        title=title,
        location=location,
        job_url=job_url,
        source=source,
        posted_at=posted_at,
        first_seen_at=now,
        last_seen_at=now,
        updated_at=now,
        is_active=True,
        is_reposted=False,
        repost_count=0,
        original_first_seen_at=now,
        description=description,
        status="NEW",
    )

    return _persist(job)


def close_old_jobs(db: Session) -> int:
    """Retire jobs that aged past the 48h window or dropped off their feed."""
    window_cutoff = live_job_cutoff()
    seen_cutoff = utcnow() - timedelta(hours=NOT_SEEN_CLOSE_HOURS)

    jobs = db.scalars(
        select(LiveJob).where(
            LiveJob.is_active.is_(True),
            or_(
                and_(
                    LiveJob.posted_at.is_not(None),
                    LiveJob.posted_at < window_cutoff,
                ),
                LiveJob.last_seen_at < seen_cutoff,
            ),
        )
    ).all()

    for job in jobs:
        job.is_active = False
        job.status = "CLOSED"
        job.updated_at = utcnow()

    if jobs:
        db.commit()

    return len(jobs)


def purge_stale_jobs(db: Session) -> int:
    """Delete long-closed rows so the table stays small."""
    cutoff = utcnow() - timedelta(days=PURGE_AFTER_DAYS)

    result = db.execute(
        delete(LiveJob).where(
            LiveJob.is_active.is_(False),
            LiveJob.updated_at < cutoff,
        )
    )
    db.commit()

    return result.rowcount or 0


def get_live_jobs(
    db: Session,
    *,
    company: str | None = None,
    only_targets: bool = False,
) -> list[LiveJob]:
    cutoff = live_job_cutoff()

    query = select(LiveJob).where(
        LiveJob.posted_at.is_not(None),
        LiveJob.posted_at >= cutoff,
    )

    if company:
        query = query.where(func.lower(LiveJob.company) == company.lower())

    query = query.order_by(LiveJob.posted_at.desc())

    rows = list(db.scalars(query).all())
    if only_targets:
        rows = [row for row in rows if is_target_company(row.company)]
    return rows


def get_summary(db: Session, *, only_targets: bool = False) -> dict[str, int]:
    cutoff = live_job_cutoff()

    jobs = db.scalars(
        select(LiveJob).where(
            LiveJob.posted_at.is_not(None),
            LiveJob.posted_at >= cutoff,
        )
    ).all()

    if only_targets:
        jobs = [job for job in jobs if is_target_company(job.company)]

    summary = {"total": len(jobs), "new": 0, "live": 0, "reposted": 0, "closed": 0}

    hour_ago = utcnow() - timedelta(hours=1)
    summary["new_last_hour"] = sum(
        1 for job in jobs if job.first_seen_at and job.first_seen_at >= hour_ago
    )

    for job in jobs:
        summary[calculate_status(job).lower()] += 1

    return summary
