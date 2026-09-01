from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from db_base import Base


class LiveJob(Base):
    __tablename__ = "live_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    company: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    external_job_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)

    location: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    job_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="linkedin",
        index=True,
    )

    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        index=True,
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    is_reposted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    repost_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    original_first_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    reposted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="NEW",
        index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "company",
            "external_job_id",
            "source",
            name="uq_live_job_company_external_source",
        ),
    )
