from live_jobs.sources import darwinbox


def test_darwinbox_parse(load_fixture):
    jobs = darwinbox.parse_jobs(
        load_fixture("darwinbox.json"), "moneyview|main"
    )

    assert len(jobs) == 3
    first = jobs[0]
    assert first.source == "darwinbox"
    assert first.external_job_id == "a688c95622ef18"
    assert first.title == "System Admin"
    # "Multiple Locations" collapses to the country
    assert first.location == "India"
    assert first.job_url == (
        "https://moneyview.darwinbox.in/ms/candidatev2/main/careers/job"
        "/a688c95622ef18"
    )
    assert first.posted_at is not None  # posted_on epoch

    assert "Bengaluru" in jobs[1].location


def test_darwinbox_parse_tolerates_garbage():
    assert darwinbox.parse_jobs(None, "t|c") == []
    assert darwinbox.parse_jobs({}, "t|c") == []
    assert darwinbox.parse_jobs({"data": "x"}, "t|c") == []


def test_darwinbox_bad_token():
    assert darwinbox.DarwinboxSource().discover("nocompany") == []
