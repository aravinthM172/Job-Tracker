"""
Persistence layer for the Job Application Tracker.

Backed by SQLite via SQLAlchemy, using the same ORM pattern already
used elsewhere in this backend (see email_sync.py). Two tables:

- Job:       one row per real-world job application (company + role).
- JobEvent:  one row per matched email (application received, interview,
             rejection, ...). Many events can belong to one Job, which is
             how multiple emails about the same job get merged instead of
             creating duplicate applications.
"""

from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

BASE_DIR = Path(__file__).resolve().parent

DATABASE_URL = f"sqlite:///{BASE_DIR / 'job_tracker.sqlite3'}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


# Order matters: higher number = more "final"/advanced stage of the
# pipeline. Used so a job's status only moves forward when a new email
# represents a more advanced (or more final) stage than what we already
# recorded, and never regresses just because emails arrive out of order.
STATUS_PRIORITY = {
    "needs_review": 0,
    "applied": 1,
    "application_received": 2,
    "assessment": 3,
    "interview": 4,
    "offer": 5,
    "rejected": 6,
}

ALL_STATUSES = list(STATUS_PRIORITY.keys())


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)

    company = Column(String(255), nullable=False, default="Unknown Company")
    role = Column(String(255), nullable=False, default="Unknown Role")
    job_id = Column(String(255), default="")

    status = Column(String(50), nullable=False, default="applied")

    source_account = Column(String(100), default="manual")

    applied_date = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    events = relationship(
        "JobEvent",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="JobEvent.received_date",
    )

    def to_dict(self, include_events=False):
        data = {
            "id": self.id,
            "company": self.company,
            "role": self.role,
            "job_id": self.job_id or "",
            "status": self.status,
            "source_account": self.source_account,
            "applied_date": iso(self.applied_date),
            "last_activity": iso(self.last_activity),
            "email_count": len(self.events),
            "created_at": iso(self.created_at),
            "updated_at": iso(self.updated_at),
        }

        latest = self.events[-1] if self.events else None

        data["latest_event"] = (
            latest.to_dict() if latest else None
        )

        if include_events:
            data["events"] = [
                e.to_dict(include_body=True) for e in self.events
            ]

        return data


class JobEvent(Base):
    __tablename__ = "job_events"

    id = Column(Integer, primary_key=True)

    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)

    event_type = Column(String(50), nullable=False)

    subject = Column(Text, default="")
    sender = Column(String(255), default="")
    account = Column(String(100), default="")

    email_id = Column(String(500), unique=True, nullable=True)
    web_link = Column(Text, default="")

    # Full email body (cleaned plain text) - only populated by syncs
    # after this column was added; older events may have "". Kept out
    # of to_dict() by default since it's fetched for every job's
    # latest_event on the list/dashboard endpoints - including it
    # there would bloat every list response with full email text.
    body = Column(Text, default="")

    received_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="events")

    def to_dict(self, include_body=False):
        data = {
            "id": self.id,
            "event_type": self.event_type,
            "subject": self.subject or "",
            "sender": self.sender or "",
            "account": self.account or "",
            "email_id": self.email_id,
            "web_link": self.web_link or "",
            "received_date": iso(self.received_date),
        }

        if include_body:
            data["body"] = self.body or ""

        return data


def iso(value):
    if not value:
        return None

    if isinstance(value, str):
        return value

    return value.isoformat()


Base.metadata.create_all(engine)


def _migrate():
    """create_all() only creates missing tables, it never alters an
    existing one - the "body" column was added after job_events
    already existed in this DB file, so it needs a manual ALTER TABLE.
    Safe to run every startup: SQLite errors (column already exists)
    are swallowed."""

    from sqlalchemy import text

    with engine.begin() as conn:
        try:
            conn.execute(
                text("ALTER TABLE job_events ADD COLUMN body TEXT DEFAULT ''")
            )
        except Exception:
            pass


_migrate()
