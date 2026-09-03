from datetime import datetime, timedelta
from pathlib import Path

from live_jobs.sources.naukri import parse_jobs, search_url, _parse_age

FIXTURE = (Path(__file__).parent / "fixtures" / "naukri.html").read_text(
    encoding="utf-8"
)


def test_search_url_slugifies_company():
    assert search_url("Goldman Sachs") == (
        "https://www.naukri.com/goldman-sachs-jobs-in-bengaluru"
    )
    assert search_url("Walmart Global Tech").endswith(
        "/walmart-global-tech-jobs-in-bengaluru"
    )


def test_parse_age_relative_forms():
    assert _parse_age("Just Now") is not None
    today = _parse_age("3 Days Ago")
    assert today is not None
    assert 2 <= (datetime.utcnow() - today) / timedelta(days=1) <= 4
    assert _parse_age("Something odd") is None


def test_parses_naukri_cards():
    jobs = parse_jobs(FIXTURE, "Google")

    assert [j.title for j in jobs] == [
        "Senior Software Engineer",
        "Data Scientist, Ads",
        "Old Role",
    ]
    assert all(j.source == "naukri" for j in jobs)
    assert all(j.company == "Google" for j in jobs)

    first = jobs[0]
    assert first.external_job_id == "140823500123"
    assert first.job_url.startswith("https://www.naukri.com/job-listings-")
    assert "Bengaluru" in (first.location or "")
    assert first.posted_at is not None
    assert first.description and "distributed systems" in first.description


def test_empty_or_blocked_html_returns_nothing():
    assert parse_jobs("", "Google") == []
    assert parse_jobs("<html><body>Press &amp; Hold</body></html>", "Google") == []
