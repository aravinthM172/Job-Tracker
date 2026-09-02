from pathlib import Path

from live_jobs.sources import google

FIXTURES = Path(__file__).parent / "fixtures"


def _raw(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_google_decode_and_parse():
    payload = google._decode(_raw("google_batchexecute.txt"))
    jobs = google.parse_jobs(payload)

    assert len(jobs) == 2

    first = jobs[0]
    assert first.company == "Google"
    assert first.source == "google"
    assert first.external_job_id == "116514262091735750"
    assert first.title == "Data Center Technician II, Hardware Operations"
    assert first.location == "Bangalore, India"  # from the loc= apply-url param
    assert first.job_url.startswith(
        "https://www.google.com/about/careers/applications/signin?jobId="
    )
    assert first.posted_at is None  # DATELESS until the date field is mapped

    assert jobs[1].location == "US"


def test_google_blocked_response_is_empty():
    # soft-block: 200 with a null payload + ["e",4,...] frame
    assert google._decode(_raw("google_blocked.txt")) is None
    assert google.parse_jobs(None) == []


def test_google_parse_tolerates_garbage():
    assert google.parse_jobs([]) == []
    assert google.parse_jobs([[["only-two-fields", "x"]]]) == []
    assert google._decode("totally not a batchexecute body") is None
