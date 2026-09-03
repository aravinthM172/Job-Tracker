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

    # parsed from title + description at read time (see routes.py) -
    # "5+ years" -> (5, None), "3-5 years" -> (3, 5), unknown -> (None, None)
    experience_min: int | None = None
    experience_max: int | None = None


class LiveJobsSummary(BaseModel):
    total: int
    new: int
    live: int
    reposted: int
    closed: int
    # postings first discovered in the last 60 minutes - drives the
    # "N new" badge on the Live Jobs nav item
    new_last_hour: int = 0
