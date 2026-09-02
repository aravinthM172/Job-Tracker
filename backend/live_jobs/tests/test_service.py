from datetime import datetime, timedelta

from live_jobs.service import (
    calculate_status,
    close_old_jobs,
    get_live_jobs,
    get_summary,
    upsert_live_job,
)


def add(db, **kw):
    base = dict(
        company="Acme",
        external_job_id="1",
        title="Engineer",
        location="Remote",
        job_url="https://e/1",
        source="fake",
        posted_at=datetime.utcnow() - timedelta(hours=1),
    )
    base.update(kw)
    return upsert_live_job(db, **base)


def test_get_live_jobs_hides_out_of_window_rows(db):
    add(db, external_job_id="fresh")
    add(
        db,
        external_job_id="stale",
        posted_at=datetime.utcnow() - timedelta(hours=100),
    )

    jobs = get_live_jobs(db)

    assert [j.external_job_id for j in jobs] == ["fresh"]


def test_get_live_jobs_company_filter_is_case_insensitive(db):
    add(db, company="Acme", external_job_id="a")
    add(db, company="Globex", external_job_id="b")

    assert len(get_live_jobs(db, company="acme")) == 1


def test_only_targets_filters_off_list_companies(db):
    add(db, company="Google", external_job_id="g")
    add(db, company="Autodesk", external_job_id="a")

    assert {j.company for j in get_live_jobs(db)} == {"Google", "Autodesk"}
    assert [j.company for j in get_live_jobs(db, only_targets=True)] == ["Google"]
    assert get_summary(db, only_targets=True)["total"] == 1


def test_summary_counts_match_list(db):
    add(db, external_job_id="a")
    add(db, external_job_id="b")

    summary = get_summary(db)

    assert summary["total"] == 2
    assert summary["new"] + summary["live"] == 2


def test_close_old_jobs_marks_closed(db):
    job = add(db, posted_at=datetime.utcnow() - timedelta(hours=100))

    assert close_old_jobs(db) == 1
    db.refresh(job)
    assert job.is_active is False
    assert job.status == "CLOSED"


def test_reposted_badge_decays_to_live():
    class Row:
        is_active = True
        is_reposted = True
        first_seen_at = datetime(2026, 1, 1)
        last_seen_at = datetime(2026, 1, 2)

    row = Row()
    row.reposted_at = datetime.utcnow() - timedelta(hours=1)
    assert calculate_status(row) == "REPOSTED"

    row.reposted_at = datetime.utcnow() - timedelta(hours=100)
    assert calculate_status(row) == "LIVE"
