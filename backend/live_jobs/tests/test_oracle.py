from live_jobs.sources import oracle


def test_oracle_parse(load_fixture):
    token = "ejgk.fa.em2.oraclecloud.com|CX_3"
    jobs = oracle.parse_jobs(load_fixture("oracle.json"), token)

    assert len(jobs) == 3
    blr = next(j for j in jobs if j.external_job_id == "30038221")
    assert blr.source == "oracle"
    assert blr.title == "Assistant Manager"
    assert blr.location == "Bangalore, Karnataka, India"
    assert blr.job_url == (
        "https://ejgk.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/"
        "sites/CX_3/job/30038221"
    )
    assert blr.posted_at is not None


def test_oracle_parse_tolerates_garbage():
    assert oracle.parse_jobs(None, "h|s") == []
    assert oracle.parse_jobs({"items": []}, "h|s") == []
    assert oracle.parse_jobs({"items": [{"requisitionList": "x"}]}, "h|s") == []


def test_oracle_bad_token():
    assert oracle.OracleSource().discover("no-pipe-here") == []
