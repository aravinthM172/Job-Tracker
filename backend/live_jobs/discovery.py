from sqlalchemy.orm import Session

from .companies import COMPANIES
from .service import upsert_live_job
from .sources.linkedin import LinkedInSource


def discover_all_companies(db: Session) -> int:
    source = LinkedInSource()
    discovered_count = 0

    for company in COMPANIES:
        try:
            jobs = source.discover_company_jobs(company)
        except Exception:
            continue

        for job in jobs:
            upsert_live_job(
                db,
                company=job.company,
                external_job_id=job.external_job_id,
                title=job.title,
                location=job.location,
                job_url=job.job_url,
                source=job.source,
                posted_at=job.posted_at,
                description=job.description,
            )
            discovered_count += 1

    return discovered_count
