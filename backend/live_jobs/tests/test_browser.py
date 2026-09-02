from pathlib import Path

from live_jobs.sources import browser

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_jobs_with_card_and_location_selector():
    html = (FIXTURES / "browser_docusign.html").read_text(encoding="utf-8")
    token = (
        "https://careers.docusign.com/careers-home/jobs?location=India"
        "###mat-expansion-panel###[class*='location']"
    )

    jobs = browser.parse_jobs(html, token)

    assert len(jobs) == 2
    first = jobs[0]
    assert first.source == "browser"
    assert first.title == "AI Engineer"
    assert first.location == "Bengaluru, Karnataka India"  # "Location " stripped
    assert first.job_url == (
        "https://careers.docusign.com/careers-home/jobs/30242"
    )
    assert first.posted_at is None  # DATELESS

    assert jobs[1].location == "Seattle, Washington United States"


def test_parse_jobs_empty_and_no_html():
    assert browser.parse_jobs("", "https://x") == []
    assert browser.parse_jobs("<html></html>", "https://x###li") == []


def test_bad_token():
    assert browser.BrowserSource().discover("not-a-url") == []
