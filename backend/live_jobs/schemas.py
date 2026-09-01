from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LiveJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company: str
    external_job_id: str | None
    title: str
    location: str | None
    job_url: str | None
    source: str
    posted_at: datetime | None
    first_seen_at: datetime
    last_seen_at: datetime
    updated_at: datetime
    is_active: bool
    is_reposted: bool
    repost_count: int
    original_first_seen_at: datetime | None
    reposted_at: datetime | None
    status: str


class LiveJobsSummary(BaseModel):
    total: int
    new: int
    live: int
    reposted: int
    closed: int
