from live_jobs.sources import goldman

_PAYLOAD = {
    "data": {
        "roleSearch": {
            "totalCount": 1014,
            "items": [
                {
                    "roleId": "182120_GS_MID_CAREER",
                    "jobTitle": "Global Banking & Markets - Software Engineer",
                    "jobFunction": "Engineering",
                    "division": "GBM",
                    "locations": [
                        {
                            "city": "Bengaluru",
                            "state": "Karnataka",
                            "country": "India",
                            "primary": True,
                        }
                    ],
                },
                {"roleId": None, "jobTitle": "bad"},
            ],
        }
    }
}


def test_goldman_parse():
    jobs = goldman.parse_jobs(_PAYLOAD)
    assert len(jobs) == 1
    j = jobs[0]
    assert j.source == "goldman"
    assert j.external_job_id == "182120_GS_MID_CAREER"
    assert j.location == "Bengaluru, Karnataka, India"
    # the detail page only accepts the numeric req id
    assert j.job_url == "https://higher.gs.com/roles/182120"
    assert j.posted_at is None


def test_goldman_parse_tolerates_garbage():
    assert goldman.parse_jobs(None) == []
    assert goldman.parse_jobs({"data": {}}) == []
    assert goldman.parse_jobs({"data": {"roleSearch": {"items": "x"}}}) == []
