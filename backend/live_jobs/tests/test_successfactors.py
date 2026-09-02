from pathlib import Path

from live_jobs.sources import successfactors

FIXTURES = Path(__file__).parent / "fixtures"


def test_successfactors_parse():
    html = (FIXTURES / "successfactors.html").read_text(encoding="utf-8")
    token = "https://jobs.volvogroup.com/search/?q=&locationsearch=India"

    jobs = successfactors.parse_jobs(html, token)

    assert len(jobs) == 2
    first = jobs[0]
    assert first.source == "successfactors"
    assert first.title == "AI / ML Engineer"
    assert first.location == "Bangalore, IN, 562122"
    assert first.job_url == (
        "https://jobs.volvogroup.com/job/Bangalore-AI-ML-Engineer-562122"
        "/1365397155/"
    )
    assert first.external_job_id == "1365397155"
    assert first.posted_at is None  # DATELESS

    assert jobs[1].location == "Gothenburg, SE"


def test_successfactors_parse_tolerates_garbage():
    assert successfactors.parse_jobs(None) == []
    assert successfactors.parse_jobs("<html>no rows</html>") == []


def test_successfactors_bad_token():
    assert successfactors.SuccessFactorsSource().discover("not-a-url") == []
