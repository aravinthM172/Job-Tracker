from live_jobs.sources import bofa


def test_bofa_parse(load_fixture):
    jobs = bofa.parse_jobs(load_fixture("bofa.json"))

    assert len(jobs) == 3
    first = jobs[0]
    assert first.company == "Bank of America"
    assert first.source == "bofa"
    assert first.external_job_id == "25048813"
    assert first.title == "Analyst- GBS - R"
    assert first.location == "Mumbai, India"
    assert first.job_url == (
        "https://careers.bankofamerica.com/en-us/job-detail/25048813"
        "/analyst-gbs-r-mumbai-india"
    )
    assert first.posted_at is not None


def test_bofa_parse_tolerates_garbage():
    assert bofa.parse_jobs(None) == []
    assert bofa.parse_jobs({}) == []
    assert bofa.parse_jobs({"jobsList": "nope"}) == []
