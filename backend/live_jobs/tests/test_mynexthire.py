from datetime import datetime, timedelta

from live_jobs import discovery
from live_jobs.models import LiveJob
from live_jobs.sources import mynexthire
from live_jobs.sources.base import DiscoveredJob


def test_mynexthire_parse(load_fixture):
    jobs = mynexthire.parse_jobs(load_fixture("swiggy.json"), "swiggy")

    assert len(jobs) == 3
    first = jobs[0]
    assert first.source == "mynexthire"
    assert first.external_job_id == "28688"
    assert first.title == "Content Executive"
    assert "swiggy.mynexthire.com" in first.job_url
    assert first.posted_at is not None


def test_mynexthire_parse_tolerates_garbage():
    assert mynexthire.parse_jobs(None, "x") == []
    assert mynexthire.parse_jobs({"reqDetailsBOList": "x"}, "x") == []


class _FakeMNH:
    name = "mynexthire"

    def discover(self, token):
        return [
            DiscoveredJob(
                company="",
                external_job_id="OLD",
                title="Old but open Bengaluru req",
                location="Bengaluru",
                job_url="https://x.mynexthire.com/employer/jobs?reqId=1",
                posted_at=datetime.utcnow() - timedelta(days=90),
                source="mynexthire",
            )
        ]


def test_dateless_source_keeps_stale_open_reqs(monkeypatch, db):
    monkeypatch.setattr(discovery, "SOURCES", {"mynexthire": _FakeMNH()})
    monkeypatch.setattr(discovery, "DATELESS_SOURCES", {"mynexthire"})
    monkeypatch.setattr(
        discovery, "COMPANY_SOURCES", {"Swiggy": [("mynexthire", "swiggy")]}
    )
    monkeypatch.setattr(discovery, "is_target_company", lambda name: True)
    monkeypatch.setattr(discovery, "_cycle", 0)

    counts = discovery.discover_all_companies(db)

    assert counts["new"] == 1
    assert counts["skipped_old"] == 0
    row = db.query(LiveJob).one()
    assert row.status in ("NEW", "LIVE")
    assert row.posted_at > datetime.utcnow() - timedelta(hours=48)
