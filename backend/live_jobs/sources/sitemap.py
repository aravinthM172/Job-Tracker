"""Careers sites scraped via their XML sitemap + JobPosting JSON-LD.

    GET {sitemap_url}                          -> list of job-detail URLs
    GET {each job url}  -> <script type="application/ld+json"> JobPosting

Works even when a site's search is a bot-walled SPA: the sitemap and the
individual job pages are published for Google for Jobs and render
server-side. ``token`` is the sitemap URL (a ``<sitemapindex>`` is
followed one level to its job sub-sitemaps).

To stay light the adapter only fetches detail pages for the most
recently modified entries (``<lastmod>``), plus any whose URL path
already names the target metro. ``datePosted`` comes from the JSON-LD;
entries without it fall back to the sitemap ``<lastmod>``.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import requests

from ..normalize import clean_location, clean_title, parse_posted_at
from .base import DiscoveredJob

_TIMEOUT = (5, 15)
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
)
_MAX_DETAIL = 50
_METRO_HINTS = ("bengaluru", "bangalore", "bangaluru")

_URL_TAG = re.compile(
    r"<url>\s*<loc>([^<]+)</loc>(?:\s*<lastmod>([^<]+)</lastmod>)?", re.I
)
_SITEMAP_LOC = re.compile(r"<sitemap>\s*<loc>([^<]+)</loc>", re.I)
_JOB_URL = re.compile(r"/job[s]?[/\-]", re.I)
_LD_BLOCK = re.compile(
    r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', re.S | re.I
)
_OG_TITLE = re.compile(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', re.I)


def _sitemap_urls(session: requests.Session, sitemap_url: str) -> list[tuple[str, str]]:
    try:
        text = session.get(sitemap_url, timeout=_TIMEOUT).text
    except requests.RequestException:
        return []

    if "<sitemapindex" in text:
        subs = _SITEMAP_LOC.findall(text)
        job_subs = [s for s in subs if re.search(r"job", s, re.I)] or subs[:2]
        entries: list[tuple[str, str]] = []
        for sub in job_subs[:3]:
            try:
                entries += _URL_TAG.findall(session.get(sub, timeout=_TIMEOUT).text)
            except requests.RequestException:
                continue
        return entries

    return _URL_TAG.findall(text)


def _job_posting(html: str) -> dict | None:
    for block in _LD_BLOCK.findall(html):
        try:
            data = json.loads(block.strip())
        except ValueError:
            continue
        for item in data if isinstance(data, list) else [data]:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                return item
    return None


def _text(value: object) -> str | None:
    """schema.org address parts are sometimes {"name": ...} objects."""
    if isinstance(value, dict):
        value = value.get("name")
    return value if isinstance(value, str) and value.strip() else None


def _location(posting: dict) -> str | None:
    loc = posting.get("jobLocation")
    if isinstance(loc, list):
        loc = loc[0] if loc else None
    if not isinstance(loc, dict):
        return None
    addr = loc.get("address")
    if not isinstance(addr, dict):
        return None
    parts = [
        _text(addr.get("addressLocality")),
        _text(addr.get("addressRegion")),
        _text(addr.get("addressCountry")),
    ]
    return clean_location(", ".join(p for p in parts if p))


def _select(entries: list[tuple[str, str]]) -> list[tuple[str, str]]:
    jobs = [(u, lm) for u, lm in entries if _JOB_URL.search(u)]
    priority = [e for e in jobs if any(h in e[0].lower() for h in _METRO_HINTS)]
    rest = sorted(
        (e for e in jobs if e not in priority),
        key=lambda e: e[1] or "",
        reverse=True,
    )
    picked = priority + rest[: max(0, _MAX_DETAIL - len(priority))]
    return picked[:_MAX_DETAIL]


def _scrape_one(
    session: requests.Session, url: str, lastmod: str
) -> DiscoveredJob | None:
    try:
        html = session.get(url, timeout=_TIMEOUT).text
    except requests.RequestException:
        return None

    posting = _job_posting(html)
    if posting:
        title = clean_title(posting.get("title"))
        location = _location(posting)
        posted_at = parse_posted_at(posting.get("datePosted"))
        external = posting.get("identifier")
        if isinstance(external, dict):
            external = external.get("value")
    else:
        og = _OG_TITLE.search(html)
        title = clean_title(og.group(1)) if og else ""
        location = None
        posted_at = None
        external = None

    if not title:
        return None

    return DiscoveredJob(
        company="",
        external_job_id=(
            str(external) if external else url.split("?")[0].rstrip("/").rsplit("/", 1)[-1]
        ),
        title=title,
        location=location,
        job_url=url,
        posted_at=posted_at or parse_posted_at(lastmod),
        source="sitemap",
    )


def discover(token: str) -> list[DiscoveredJob]:
    session = requests.Session()
    session.headers.update({"User-Agent": _UA})

    picked = _select(_sitemap_urls(session, token))
    if not picked:
        return []

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = pool.map(lambda e: _scrape_one(session, e[0], e[1]), picked)

    return [job for job in results if job is not None]


class SitemapSource:
    name = "sitemap"

    def discover(self, token: str) -> list[DiscoveredJob]:
        if not token.startswith("http"):
            return []
        try:
            return discover(token)
        except Exception:
            return []
