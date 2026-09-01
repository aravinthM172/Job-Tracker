from datetime import datetime

from live_jobs.normalize import (
    clean_location,
    clean_title,
    fallback_external_id,
    normalize_company,
    parse_posted_at,
)


def test_clean_title_strips_tags_and_whitespace():
    assert clean_title("  <b>Staff</b>   Engineer\n") == "Staff Engineer"
    assert clean_title(None) == ""


def test_clean_location_none_for_empty():
    assert clean_location("") is None
    assert clean_location("  ,;  ") is None
    assert clean_location("Bengaluru, IN ") == "Bengaluru, IN"


def test_normalize_company():
    assert normalize_company("Match Group, Inc.") == "match group inc"
    assert normalize_company(None) == ""


def test_parse_posted_at_iso():
    assert parse_posted_at("2026-04-17T05:58:03-04:00") == datetime(2026, 4, 17, 9, 58, 3)


def test_parse_posted_at_epoch_millis():
    # Lever createdAt (ms)
    assert parse_posted_at(1786057390514) == datetime.utcfromtimestamp(1786057390.514)


def test_parse_posted_at_human_double_space():
    # Amazon posted_date
    assert parse_posted_at("September  1, 2026") == datetime(2026, 9, 1)


def test_parse_posted_at_unparseable():
    assert parse_posted_at("") is None
    assert parse_posted_at("someday soon") is None
    assert parse_posted_at(None) is None


def test_fallback_external_id_is_stable_and_prefixed():
    a = fallback_external_id("Acme", "SWE", "NYC", "https://x/y?utm=1")
    b = fallback_external_id("Acme", "SWE", "NYC", "https://x/y?utm=2")
    assert a == b  # query string ignored
    assert a.startswith("fb_")
    assert a != fallback_external_id("Acme", "SWE II", "NYC", "https://x/y")
