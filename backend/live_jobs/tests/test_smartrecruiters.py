from live_jobs.sources import smartrecruiters


def test_smartrecruiters_parse(load_fixture):
    jobs = smartrecruiters.parse_jobs(
        load_fixture("smartrecruiters.json"), "ServiceNow"
    )

    assert len(jobs) == 3

    first = jobs[0]
    assert first.source == "smartrecruiters"
    assert first.external_job_id == "744000146789639"
    assert first.title == "Staff Software Engineer - Infrastructure"
    assert first.location == "Hyderabad, India"  # empty region collapsed
    assert first.job_url == (
        "https://jobs.smartrecruiters.com/ServiceNow/744000146789639"
    )
    assert first.posted_at is not None

    assert jobs[2].location == "Hyderabad, Telangana, India"


def test_smartrecruiters_parse_tolerates_garbage():
    assert smartrecruiters.parse_jobs(None, "X") == []
    assert smartrecruiters.parse_jobs({}, "X") == []
    assert smartrecruiters.parse_jobs({"content": "nope"}, "X") == []
