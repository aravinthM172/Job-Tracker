from live_jobs.sources import phenom


def test_phenom_parse(load_fixture):
    jobs = phenom.parse_jobs(load_fixture("phenom.json"), "careers.cisco.com")

    assert len(jobs) == 2
    swe = jobs[0]
    assert swe.source == "phenom"
    assert swe.external_job_id == "2020452"
    assert swe.title == "Software Engineer"
    assert swe.location == "Bengaluru, Karnataka, India"
    # applyUrl with the trailing /apply trimmed
    assert swe.job_url.endswith("Software-Engineer_2020452-1")
    assert swe.posted_at is not None
    assert "5 years" in swe.description


def test_phenom_parse_tolerates_garbage():
    assert phenom.parse_jobs(None, "h") == []
    assert phenom.parse_jobs({"refineSearch": {}}, "h") == []
    assert phenom.parse_jobs({"refineSearch": {"data": {"jobs": "x"}}}, "h") == []


def test_phenom_bad_token():
    assert phenom.PhenomSource().discover("not-a-host") == []
    assert phenom.PhenomSource().discover("") == []
