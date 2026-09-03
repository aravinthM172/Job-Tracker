from live_jobs.sources import eightfold
from live_jobs.sources.base import DiscoveredJob


def test_eightfold_parse(load_fixture):
    token = "apply.careers.microsoft.com|microsoft.com"
    jobs = eightfold.parse_jobs(load_fixture("eightfold.json"), token)

    assert len(jobs) == 2
    first = jobs[0]
    assert first.source == "eightfold"
    assert first.external_job_id == "200053022"
    assert first.title == "Senior Product Manager"
    assert first.location == "India, Karnataka, Bangalore"
    assert first.job_url == (
        "https://apply.careers.microsoft.com/careers/job/1970393556984528"
    )
    assert first.posted_at is not None  # epoch postedTs


def test_eightfold_parse_tolerates_garbage():
    assert eightfold.parse_jobs(None, "h|d") == []
    assert eightfold.parse_jobs({"data": {}}, "h|d") == []
    assert eightfold.parse_jobs({"data": {"positions": "nope"}}, "h|d") == []


def test_eightfold_bad_token():
    assert eightfold.EightfoldSource().discover("no-pipe") == []


def test_eightfold_enrich_uses_internal_id(monkeypatch):
    job = DiscoveredJob(
        company="",
        external_job_id="200053022",
        title="Senior PM",
        location="Bengaluru",
        job_url="https://apply.careers.microsoft.com/careers/job/1970393556984528",
        posted_at=None,
        source="eightfold",
    )
    job.posted_at = __import__("datetime").datetime.utcnow()

    seen = {}

    def fake_get_json(url, params=None):
        seen["position_id"] = params.get("position_id")
        return {"data": {"positions": [{"jobDescription": "<p>Need 6+ years.</p>"}]}}

    monkeypatch.setattr(eightfold, "get_json", fake_get_json)
    eightfold._enrich([job], "apply.careers.microsoft.com", "microsoft.com")

    assert seen["position_id"] == "1970393556984528"
    assert job.description == "Need 6+ years."
