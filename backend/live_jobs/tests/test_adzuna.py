from live_jobs.sources import adzuna


def test_adzuna_matches_target_companies(load_fixture):
    targets = {
        adzuna.normalize_company("Flipkart"): "Flipkart",
        adzuna.normalize_company("EPAM Systems"): "EPAM Systems",
    }
    jobs = adzuna.parse_jobs(load_fixture("adzuna.json"), targets)

    # "Some Staffing Agency" dropped; "EPAM Systems Limited" ~matches target
    assert {j.company for j in jobs} == {"Flipkart", "EPAM Systems"}

    flip = next(j for j in jobs if j.company == "Flipkart")
    assert flip.source == "adzuna"
    assert flip.title == "Senior Software Engineer, Platform"
    assert flip.location == "Bengaluru, Karnataka"
    assert flip.external_job_id == "5012345678"
    assert flip.posted_at is not None


def test_adzuna_parse_tolerates_garbage():
    assert adzuna.parse_jobs(None, {}) == []
    assert adzuna.parse_jobs({"results": "x"}, {}) == []


def test_adzuna_no_key_is_noop(monkeypatch):
    monkeypatch.delenv("ADZUNA_APP_ID", raising=False)
    monkeypatch.delenv("ADZUNA_APP_KEY", raising=False)
    assert adzuna.AdzunaSource().discover("") == []
