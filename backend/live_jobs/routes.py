from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db import SessionLocal
from .schemas import LiveJobResponse, LiveJobsSummary
from .service import get_live_jobs, get_summary

router = APIRouter(prefix="/api/live-jobs", tags=["Live Jobs"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=list[LiveJobResponse])
def list_live_jobs(
    company: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return get_live_jobs(db, company=company, only_targets=True)


@router.get("/summary", response_model=LiveJobsSummary)
def live_jobs_summary(db: Session = Depends(get_db)):
    return get_summary(db, only_targets=True)
