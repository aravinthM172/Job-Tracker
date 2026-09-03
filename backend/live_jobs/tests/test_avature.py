from live_jobs.sources import avature

_HTML = """
<html><body>
<article class="article article--result">
  <div class="article__header__text">
    <h3 class="article__header__text__title">
      <a class="link" href="https://jobsearch.harman.com/en_US/careers/JobDetail/Senior-Firmware-Engineer/59985">Senior Firmware Engineer</a>
    </h3>
    <div class="article__header__text__subtitle">
      <span class="list-item-location"><strong>Location:</strong> Bengaluru, Karnataka, India</span>
      <span class="list-item-ref"><strong>Ref #</strong> R-1</span>
      <span class="list-item-posted"><strong>Date Posted:</strong> 31-Jul-2026</span>
    </div>
  </div>
</article>
<article class="article article--result">
  <h3><a href="/en_US/careers/JobDetail/x/60001">DSP Engineer</a></h3>
  <div class="article__header__text__subtitle">
    <span class="list-item-location"><strong>Location:</strong> Pune, India</span>
  </div>
</article>
</body></html>
"""


def test_avature_parse():
    jobs = avature.parse_jobs(_HTML, "https://jobsearch.harman.com/en_US/careers/SearchJobs/")
    assert len(jobs) == 2
    j = jobs[0]
    assert j.source == "avature"
    assert j.external_job_id == "59985"
    assert j.title == "Senior Firmware Engineer"
    assert j.location == "Bengaluru, Karnataka, India"
    assert j.job_url == (
        "https://jobsearch.harman.com/en_US/careers/JobDetail/Senior-Firmware-Engineer/59985"
    )
    assert j.posted_at is not None  # parsed from "31-Jul-2026"


def test_avature_parse_tolerates_garbage():
    assert avature.parse_jobs("", "https://x") == []
    assert avature.parse_jobs("<html>no results here</html>", "https://x") == []


def test_avature_bad_token():
    assert avature.AvatureSource().discover("not-a-url") == []
