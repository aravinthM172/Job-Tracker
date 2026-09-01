from datetime import datetime, timedelta

import pytest

from live_jobs import discovery
from live_jobs.models import LiveJob
from live_jobs.sources.base import DiscoveredJob


class FakeSource:
    name = "fake"

    def __init__(self, jobs):
        self._jobs = jobs

    def discover(self, token):
        return [DiscoveredJob(**{**j}) for j in self._jobs]


def make_job(**overrides):
    base = dict(
        company="",
        external_job_id="req-1",
        title="Software Engineer",
        location="Bengaluru, IN",
        job_url="https://careers.acme.com/req-1",
        posted_at=datetime.utcnow() - timedelta(hours=2),
        description=None,
        source="fake",
    )
    base.update(overrides)
    return base


@pytest.fixture
def run_discovery(monkeypatch, db):
    def _run(jobs):
        monkeypatch.setattr(discovery, "SOURCES", {"fake": FakeSource(jobs)})
        monkeypatch.setattr(
            discovery, "COMPANY_SOURCES", {"Acme": [("fake", "acme")]}
        )
        return discovery.discover_all_companies(db)

    return _run


def test_fresh_job_is_inserted(run_discovery, db):
    counts = run_discovery([make_job()])

    assert counts["new"] == 1
    assert counts["updated"] == 0
    rows = db.query(LiveJob).all()
    assert len(rows) == 1
    assert rows[0].company == "Acme"
    assert rows[0].status == "NEW"
    assert rows[0].external_job_id == "req-1"


def test_rerun_updates_not_duplicates(run_discovery, db):
    run_discovery([make_job()])
    counts = run_discovery([make_job(title="Software Engineer II")])

    assert counts["new"] == 0
    assert counts["updated"] == 1
    rows = db.query(LiveJob).all()
    assert len(rows) == 1
    assert rows[0].title == "Software Engineer II"
    assert rows[0].status == "LIVE"


def test_old_job_is_skipped(run_discovery, db):
    counts = run_discovery(
        [make_job(posted_at=datetime.utcnow() - timedelta(hours=72))]
    )

    assert counts["skipped_old"] == 1
    assert counts["new"] == 0
    assert db.query(LiveJob).count() == 0


def test_job_without_posted_at_is_invalid(run_discovery, db):
    counts = run_discovery([make_job(posted_at=None)])

    assert counts["skipped_invalid"] == 1
    assert db.query(LiveJob).count() == 0


def test_missing_external_id_uses_stable_fallback(run_discovery, db):
    run_discovery([make_job(external_job_id=None)])
    counts = run_discovery([make_job(external_job_id=None)])

    assert counts["new"] == 0 and counts["updated"] == 1
    row = db.query(LiveJob).one()
    assert row.external_job_id.startswith("fb_")


def test_repost_detection(run_discovery, db):
    from live_jobs.service import close_old_jobs

    run_discovery([make_job()])

    # job drops off the feed and ages out
    row = db.query(LiveJob).one()
    row.posted_at = datetime.utcnow() - timedelta(hours=72)
    db.commit()
    assert close_old_jobs(db) == 1

    # it comes back, fresh
    run_discovery([make_job()])
    row = db.query(LiveJob).one()
    assert row.is_reposted is True
    assert row.repost_count == 1
    assert row.status == "REPOSTED"
