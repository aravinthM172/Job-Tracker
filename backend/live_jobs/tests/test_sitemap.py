from pathlib import Path

from live_jobs.sources import sitemap

FIXTURES = Path(__file__).parent / "fixtures"


def test_job_posting_and_location():
    html = (FIXTURES / "sitemap_intuit_job.html").read_text(encoding="utf-8")

    posting = sitemap._job_posting(html)
    assert posting is not None
    assert posting["title"] == "Senior Staff Software Engineer"

    loc = sitemap._location(posting)
    assert loc is not None
    assert "Bangalore" in loc and "India" in loc


def test_job_posting_none_when_absent():
    assert sitemap._job_posting("<html><body>no ld json</body></html>") is None
    assert sitemap._job_posting('<script type="application/ld+json">{}</script>') is None


def test_select_prioritises_metro_then_recent_lastmod():
    entries = [
        ("https://x.com/job/london/a/1", "2026-09-02"),
        ("https://x.com/job/bengaluru/b/2", "2026-01-01"),
        ("https://x.com/job/paris/c/3", "2026-09-01"),
        ("https://x.com/not-a-job/d", "2026-09-03"),
    ]
    picked = [u for u, _ in sitemap._select(entries)]

    assert picked[0] == "https://x.com/job/bengaluru/b/2"  # metro hint first
    assert "https://x.com/not-a-job/d" not in picked  # non-job dropped
    assert picked[1] == "https://x.com/job/london/a/1"  # then newest lastmod


def test_bad_token():
    assert sitemap.SitemapSource().discover("not-a-url") == []
