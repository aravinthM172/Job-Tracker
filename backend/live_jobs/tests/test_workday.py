from datetime import datetime, timedelta

from live_jobs.normalize import parse_posted_at
from live_jobs.sources import workday


def test_parse_relative_dates():
    today_midnight = datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    assert parse_posted_at("Posted Today") == today_midnight
    assert parse_posted_at("Posted Yesterday") == today_midnight - timedelta(days=1)
    assert parse_posted_at("Posted 5 Days Ago") == today_midnight - timedelta(days=5)
    assert parse_posted_at("Posted 30+ Days Ago") == today_midnight - timedelta(
        days=30
    )


def test_workday_parse(load_fixture):
    token = "nvidia/wd5/NVIDIAExternalCareerSite"
    jobs = workday.parse_jobs(load_fixture("workday.json"), token)

    assert jobs
    first = jobs[0]
    assert first.source == "workday"
    assert first.external_job_id == "JR2023286"
    assert first.title.startswith("Business Operations Technical Program Manager")
    assert first.location == "US, CA, Santa Clara"
    assert first.job_url == (
        "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"
        "/job/US-CA-Santa-Clara/"
        "Business-Operations-Technical-Program-Manager---DGX-Cloud_JR2023286"
    )
    assert first.posted_at is not None


def test_workday_parse_tolerates_garbage():
    assert workday.parse_jobs(None, "a/b/c") == []
    assert workday.parse_jobs({"jobPostings": "nope"}, "a/b/c") == []


def test_workday_bad_token_returns_nothing():
    assert workday.WorkdaySource().discover("not-a-valid-token") == []


def test_workday_enrich_fills_description(monkeypatch):
    from live_jobs.sources.base import DiscoveredJob

    job = DiscoveredJob(
        company="",
        external_job_id="JR1",
        title="Staff Engineer",
        location="Bengaluru",
        job_url=(
            "https://nvidia.wd5.myworkdayjobs.com/en-US/Site/job/India/"
            "Staff-Engineer_JR1"
        ),
        posted_at=datetime.utcnow(),
        source="workday",
    )

    monkeypatch.setattr(
        workday,
        "get_json",
        lambda url: {"jobPostingInfo": {"jobDescription": "<p>Need 7+ years.</p>"}},
    )
    workday._enrich([job], "nvidia", "wd5", "Site")

    assert job.description == "Need 7+ years."
