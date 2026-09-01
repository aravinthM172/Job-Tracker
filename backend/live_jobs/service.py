from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import LiveJob


LOOKBACK_HOURS = 48


def utcnow() -> datetime:
    return datetime.utcnow()


def live_job_cutoff() -> datetime:
    return utcnow() - timedelta(hours=LOOKBACK_HOURS)


def calculate_status(job: LiveJob) -> str:
    if job.is_reposted:
        return "REPOSTED"

    if job.is_active:
        return "NEW" if job.first_seen_at == job.last_seen_at else "LIVE"

    return "CLOSED"


def upsert_live_job(
    db: Session,
    *,
    company: str,
    external_job_id: str | None,
    title: str,
    location: str | None = None,
    job_url: str | None = None,
    source: str = "linkedin",
    posted_at: datetime | None = None,
    description: str | None = None,
) -> LiveJob:

    now = utcnow()

    existing = None

    if external_job_id:
        existing = db.scalar(
            select(LiveJob).where(
                LiveJob.company == company,
                LiveJob.external_job_id == external_job_id,
                LiveJob.source == source,
            )
        )

    if existing:
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

        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

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

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


def close_old_jobs(db: Session) -> int:
    cutoff = live_job_cutoff()

    jobs = db.scalars(
        select(LiveJob).where(
            LiveJob.is_active.is_(True),
            LiveJob.posted_at.is_not(None),
            LiveJob.posted_at < cutoff,
        )
    ).all()

    count = 0

    for job in jobs:
        job.is_active = False
        job.status = "CLOSED"
        job.updated_at = utcnow()
        count += 1

    if count:
        db.commit()

    return count


def get_live_jobs(
    db: Session,
    *,
    company: str | None = None,
) -> list[LiveJob]:

    cutoff = live_job_cutoff()

    query = select(LiveJob).where(
        LiveJob.posted_at.is_not(None),
        LiveJob.posted_at >= cutoff,
    )

    if company:
        query = query.where(
            func.lower(LiveJob.company) == company.lower()
        )

    query = query.order_by(LiveJob.posted_at.desc())

    return list(db.scalars(query).all())


def get_summary(db: Session) -> dict[str, int]:
    cutoff = live_job_cutoff()

    jobs = db.scalars(
        select(LiveJob).where(
            LiveJob.posted_at.is_not(None),
            LiveJob.posted_at >= cutoff,
        )
    ).all()

    summary = {
        "total": len(jobs),
        "new": 0,
        "live": 0,
        "reposted": 0,
        "closed": 0,
    }

    for job in jobs:
        status = calculate_status(job)
        summary[status.lower()] += 1

    return summary
