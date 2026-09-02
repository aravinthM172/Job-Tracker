from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db import SessionLocal
from .models import LiveJob
from .normalize import parse_experience
from .schemas import LiveJobResponse, LiveJobsSummary
from .service import get_live_jobs, get_summary

router = APIRouter(prefix="/api/live-jobs", tags=["Live Jobs"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _to_response(job: LiveJob) -> LiveJobResponse:
    payload = LiveJobResponse.model_validate(job)
    lo, hi = parse_experience(f"{job.title}\n{job.description or ''}")
    payload.experience_min = lo
    payload.experience_max = hi
    return payload


@router.get("", response_model=list[LiveJobResponse])
def list_live_jobs(
    company: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    jobs = get_live_jobs(db, company=company, only_targets=True)
    return [_to_response(job) for job in jobs]


@router.get("/summary", response_model=LiveJobsSummary)
def live_jobs_summary(db: Session = Depends(get_db)):
    return get_summary(db, only_targets=True)
