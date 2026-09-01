from datetime import datetime, timedelta

import pytest

from live_jobs import discovery
from live_jobs.models import LiveJob
from live_jobs.sources import swiggy
from live_jobs.sources.base import DiscoveredJob


def test_swiggy_parse(load_fixture):
    jobs = swiggy.parse_jobs(load_fixture("swiggy.json"))

    assert len(jobs) == 3
    first = jobs[0]
    assert first.company == "Swiggy"
    assert first.source == "swiggy"
    assert first.external_job_id == "28688"
    assert first.title == "Content Executive"
    assert first.job_url == "https://careers.swiggy.com/#/careers/28688"
    assert first.posted_at is not None


def test_swiggy_parse_tolerates_garbage():
    assert swiggy.parse_jobs(None) == []
    assert swiggy.parse_jobs({"reqDetailsBOList": "x"}) == []


class _FakeSwiggy:
    name = "swiggy"

    def discover(self, token):
        return [
            DiscoveredJob(
                company="",
                external_job_id="OLD",
                title="Old but open Bengaluru req",
                location="Bengaluru",
                job_url="https://careers.swiggy.com/#/careers/1",
                posted_at=datetime.utcnow() - timedelta(days=90),  # stale
                source="swiggy",
            )
        ]


def test_dateless_source_keeps_stale_open_reqs(monkeypatch, db):
    monkeypatch.setattr(discovery, "SOURCES", {"swiggy": _FakeSwiggy()})
    monkeypatch.setattr(discovery, "DATELESS_SOURCES", {"swiggy"})
    monkeypatch.setattr(discovery, "COMPANY_SOURCES", {"Swiggy": [("swiggy", "")]})
    monkeypatch.setattr(discovery, "_cycle", 0)

    counts = discovery.discover_all_companies(db)

    assert counts["new"] == 1
    assert counts["skipped_old"] == 0
    row = db.query(LiveJob).one()
    assert row.status in ("NEW", "LIVE")
    # clamped into the window, not left at the 90-day-old date
    assert row.posted_at > datetime.utcnow() - timedelta(hours=48)
