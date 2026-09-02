from live_jobs.sources import keka


def test_keka_parse(load_fixture):
    token = "jupiter|b5279857-cf81-4dde-a215-fc48957ee2b5"
    jobs = keka.parse_jobs(load_fixture("keka.json"), token)

    assert len(jobs) == 3
    first = jobs[0]
    assert first.source == "keka"
    assert first.external_job_id == "138159"
    assert first.title == "Legal Associate"
    assert first.location == "Bengaluru, KA, India"
    assert first.job_url == (
        "https://jupiter.keka.com/careers/jobdetails/138159"
    )
    assert first.posted_at is not None


def test_keka_parse_tolerates_garbage():
    assert keka.parse_jobs(None, "t|p") == []
    assert keka.parse_jobs({}, "t|p") == []
    assert keka.parse_jobs([{"id": 1}], "t|p")[0].title == ""


def test_keka_bad_token():
    assert keka.KekaSource().discover("noportal") == []
