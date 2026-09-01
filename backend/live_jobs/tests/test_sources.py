"""Parse recorded real responses from each source - no network."""

from datetime import datetime

from live_jobs.sources import ashby, amazon, greenhouse, lever


def test_greenhouse_parse(load_fixture):
    jobs = greenhouse.parse_jobs(load_fixture("greenhouse.json"))

    assert len(jobs) == 3
    first = jobs[0]
    assert first.source == "greenhouse"
    assert first.external_job_id == "8503792002"
    assert first.title == "Account Executive - Italy"
    assert first.location == "Remote, Italy"
    assert first.job_url.startswith("https://")
    assert first.posted_at == datetime(2026, 4, 17, 9, 58, 3)


def test_lever_parse(load_fixture):
    jobs = lever.parse_jobs(load_fixture("lever.json"))

    assert jobs
    first = jobs[0]
    assert first.source == "lever"
    assert first.external_job_id == "a538a1ca-0b76-46d1-a933-d43dbe7f5c83"
    assert first.title == "Brand & Community Manager"
    assert first.location == "MX"
    assert first.job_url == "https://jobs.lever.co/tala/a538a1ca-0b76-46d1-a933-d43dbe7f5c83"
    assert first.posted_at is not None


def test_ashby_parse_strips_title_and_skips_unlisted(load_fixture):
    data = load_fixture("ashby.json")
    data["jobs"][1]["isListed"] = False

    jobs = ashby.parse_jobs(data)

    assert len(jobs) == 2  # one unlisted dropped
    first = jobs[0]
    assert first.source == "ashby"
    assert first.title == "Security Engineer, Cloud"  # leading space trimmed
    assert first.job_url.startswith("https://jobs.ashbyhq.com/")
    assert first.posted_at == datetime(2026, 4, 7, 17, 12, 35, 753000)


def test_amazon_parse(load_fixture):
    jobs = amazon.parse_jobs(load_fixture("amazon.json"))

    assert jobs
    first = jobs[0]
    assert first.company == "Amazon"
    assert first.source == "amazon"
    assert first.external_job_id == "10524368"
    assert first.job_url == "https://www.amazon.jobs/en/jobs/10524368/critical-infrastructure-mechanical-engineer-field-engineering"
    assert first.posted_at == datetime(2026, 9, 1)


def test_parsers_tolerate_garbage():
    assert greenhouse.parse_jobs(None) == []
    assert greenhouse.parse_jobs({"jobs": "nope"}) == []
    assert lever.parse_jobs({"not": "a list"}) == []
    assert ashby.parse_jobs([]) == []
    assert amazon.parse_jobs(None) == []
