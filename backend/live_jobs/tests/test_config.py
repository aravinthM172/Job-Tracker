import pytest

from live_jobs.config import location_filter, location_matches


def test_location_matches_semantics():
    frags = ["bengaluru", "bangalore", "karnataka"]
    assert location_matches("Bengaluru, Karnataka, India", frags)
    assert location_matches("IN-KA-Bangalore", frags)
    assert location_matches("Remote - Bangalore", frags)
    assert not location_matches("Mumbai, Maharashtra, India", frags)
    assert not location_matches("2 Locations", frags)
    assert not location_matches(None, frags)


def test_empty_filter_keeps_everything():
    assert location_matches("Anywhere", [])
    assert location_matches(None, [])


def test_location_filter_reads_env(monkeypatch):
    monkeypatch.setenv("LIVE_JOBS_LOCATIONS", "india, remote")
    assert location_filter() == ["india", "remote"]

    monkeypatch.setenv("LIVE_JOBS_LOCATIONS", "")
    assert location_filter() == []

    monkeypatch.delenv("LIVE_JOBS_LOCATIONS")
    frags = location_filter()
    assert "bengaluru" in frags
    assert "hyderabad" in frags


def test_default_filter_keeps_both_metros(monkeypatch):
    monkeypatch.delenv("LIVE_JOBS_LOCATIONS", raising=False)
    frags = location_filter()
    assert location_matches("Hyderabad, Telangana, India", frags)
    assert location_matches("Bengaluru, Karnataka, India", frags)
    assert not location_matches("Pune, Maharashtra, India", frags)
