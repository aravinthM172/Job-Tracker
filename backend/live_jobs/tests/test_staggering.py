"""Heavy sources (workday / amazon) run only every 3rd cycle."""

from datetime import datetime

import pytest

from live_jobs import discovery
from live_jobs.models import LiveJob
from live_jobs.sources.base import DiscoveredJob


class RecordingSource:
    def __init__(self, name):
        self.name = name
        self.calls = 0

    def discover(self, token):
        self.calls += 1
        return [
            DiscoveredJob(
                company="",
                external_job_id=f"{self.name}-1",
                title="Engineer",
                location="Remote",
                job_url=f"https://x/{self.name}",
                posted_at=datetime.utcnow(),
                source=self.name,
            )
        ]


@pytest.fixture
def wired(monkeypatch):
    light = RecordingSource("greenhouse")
    heavy = RecordingSource("workday")
    monkeypatch.setattr(
        discovery, "SOURCES", {"greenhouse": light, "workday": heavy}
    )
    monkeypatch.setattr(discovery, "HEAVY_SOURCES", {"workday"})
    monkeypatch.setattr(
        discovery,
        "COMPANY_SOURCES",
        {
            "Acme": [("greenhouse", "acme")],
            "BigCo": [("workday", "bigco/wd1/x")],
        },
    )
    monkeypatch.setattr(discovery, "_cycle", 0)
    return light, heavy


def test_heavy_source_runs_every_third_cycle(wired, db):
    light, heavy = wired

    for _ in range(6):
        discovery.discover_all_companies(db)

    assert light.calls == 6  # every cycle
    assert heavy.calls == 2  # cycles 1 and 4

    # both companies' jobs still land eventually
    companies = {row.company for row in db.query(LiveJob).all()}
    assert companies == {"Acme", "BigCo"}
