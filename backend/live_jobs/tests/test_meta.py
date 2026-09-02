from live_jobs.sources import meta


def test_meta_parse(load_fixture):
    jobs = meta.parse_jobs(load_fixture("meta.json"))

    # only all_jobs - featured_jobs (often another region) are ignored
    assert len(jobs) == 3

    first = jobs[0]
    assert first.company == "Meta"
    assert first.source == "meta"
    assert first.external_job_id == "1721254462523213"
    assert first.title == "Client Solutions Manager, Ecommerce"
    assert first.location == "Bangalore, India"
    assert first.job_url == (
        "https://www.metacareers.com/jobs/1721254462523213/"
    )
    assert first.posted_at is None  # DATELESS

    multi = jobs[2]
    assert multi.location == "Bangalore, India; Gurgaon, India; Mumbai, India"


def test_meta_parse_tolerates_garbage():
    assert meta.parse_jobs(None) == []
    assert meta.parse_jobs({}) == []
    assert meta.parse_jobs({"data": {}}) == []
    assert meta.parse_jobs({"data": {"job_search_with_featured_jobs_v2": {}}}) == []
    # stale doc_id -> Meta answers 200 with an errors body
    assert meta.parse_jobs({"errors": [{"message": "..."}]}) == []
