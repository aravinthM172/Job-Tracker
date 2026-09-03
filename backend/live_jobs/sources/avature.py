"""Avature ATS careers sites (the "SearchJobs" server-rendered list).

    GET {search_url}&jobRecordsPerPage=20&jobOffset={n}

Unauthenticated, server-rendered HTML. ``token`` is the full SearchJobs
URL including any location facet, e.g.
``"https://jobsearch.harman.com/en_US/careers/SearchJobs/?2039=%5B59985%5D&2039_format=2669"``.
Each posting is an ``article.article--result`` with the title in
``h3 a`` (href ends ``/JobDetail/<slug>/<id>``) and the location as the
last ``span`` of ``.article__header__text__subtitle``. Avature rarely
exposes a post date, so this is a DATELESS source.
"""

from __future__ import annotations

import re

from ..normalize import clean_location, clean_title
from .base import DiscoveredJob, get_text

_PAGE_SIZE = 20
_MAX_PAGES = 5
_ID = re.compile(r"/JobDetail/[^/]+/(\d+)")


def parse_jobs(html: str, base_url: str = "") -> list[DiscoveredJob]:
    if not html or "article--result" not in html:
        return []

    try:
        from bs4 import BeautifulSoup
    except ImportError:  # pragma: no cover
        return []

    origin_match = re.match(r"https?://[^/]+", base_url)
    origin = origin_match.group(0) if origin_match else ""

    soup = BeautifulSoup(html, "html.parser")
    jobs: list[DiscoveredJob] = []

    for art in soup.select("article.article--result"):
        anchor = art.select_one("h3 a[href]") or art.find("a", href=True)
        if anchor is None:
            continue
        title = clean_title(anchor.get_text(" "))
        if not title:
            continue
        href = anchor["href"]
        job_url = href if href.startswith("http") else origin + href

        loc = None
        spans = art.select(".article__header__text__subtitle span")
        if spans:
            loc = clean_location(spans[-1].get_text(" "))

        id_match = _ID.search(href)
        jobs.append(
            DiscoveredJob(
                company="",
                external_job_id=(
                    id_match.group(1)
                    if id_match
                    else re.sub(r"\W+", "", href)[-24:] or None
                ),
                title=title,
                location=loc,
                job_url=job_url,
                posted_at=None,  # Avature SearchJobs carries no post date
                source="avature",
            )
        )

    return jobs


class AvatureSource:
    name = "avature"

    def discover(self, token: str) -> list[DiscoveredJob]:
        if not token.startswith("http"):
            return []

        sep = "&" if "?" in token else "?"
        jobs: list[DiscoveredJob] = []
        seen: set[str] = set()

        for page in range(_MAX_PAGES):
            url = f"{token}{sep}jobRecordsPerPage={_PAGE_SIZE}&jobOffset={page * _PAGE_SIZE}"
            batch = parse_jobs(get_text(url), token)
            new = [j for j in batch if j.external_job_id not in seen]
            if not new:
                break
            for j in new:
                seen.add(j.external_job_id)
            jobs.extend(new)
            if len(batch) < _PAGE_SIZE:
                break

        return jobs
