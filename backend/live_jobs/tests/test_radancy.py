from datetime import datetime, timedelta

from live_jobs.sources import radancy


def test_radancy_parse_with_dates(load_fixture):
    jobs = radancy.parse_jobs(
        load_fixture("radancy_synopsys.json"), "https://careers.synopsys.com"
    )

    assert len(jobs) >= 2
    first = jobs[0]
    assert first.source == "radancy"
    assert first.external_job_id == "100032391280"
    assert first.title == "Analog Design, Sr Engineer"
    assert first.location == "Noida, India"
    assert first.job_url == (
        "https://careers.synopsys.com/job/noida/analog-design-sr-engineer"
        "/44408/100032391280"
    )
    assert first.posted_at is not None  # real MM/DD/YYYY on the card


def test_radancy_parse_no_card_date(load_fixture):
    jobs = radancy.parse_jobs(
        load_fixture("radancy_arm.json"), "https://careers.arm.com"
    )

    assert len(jobs) >= 1
    first = jobs[0]
    assert first.external_job_id == "100031425824"
    assert first.title == "Staff Software Engineer – SoC SW Productisation"
    assert first.location == "Bengaluru, India"
    assert first.posted_at is None  # no date on the card; filled in later


def test_radancy_fill_undated_caps_and_synthesises():
    now = datetime.utcnow()
    dated = radancy.DiscoveredJob(
        company="", external_job_id="d", title="t", location="Bengaluru",
        job_url="u", posted_at=now, source="radancy",
    )
    undated = [
        radancy.DiscoveredJob(
            company="", external_job_id=str(i), title="t", location="Bengaluru",
            job_url="u", posted_at=None, source="radancy",
        )
        for i in range(radancy._MAX_UNDATED + 10)
    ]

    out = radancy._fill_undated([dated, *undated])

    # dated one kept as-is + exactly _MAX_UNDATED of the undated
    assert len(out) == 1 + radancy._MAX_UNDATED
    assert out[0].posted_at == now
    assert all(j.posted_at is not None for j in out)
    assert all(
        j.posted_at > now - timedelta(hours=48) for j in out[1:]
    )


def test_radancy_parse_tolerates_garbage():
    assert radancy.parse_jobs(None, "https://x") == []
    assert radancy.parse_jobs({}, "https://x") == []
    assert radancy.parse_jobs({"results": ""}, "https://x") == []
    assert radancy.parse_jobs({"results": "<li>no link here</li>"}, "https://x") == []


def test_radancy_bad_token():
    assert radancy.RadancySource().discover("careers.synopsys.com") == []
