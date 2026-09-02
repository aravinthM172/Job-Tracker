"""Headless-browser fallback for careers sites that render jobs only in JS.

    token = "<search-results URL>"  or
            "<search-results URL>###<css selector for one job card>"

The optional card selector makes extraction reliable on sites whose
markup the generic heuristic can't read; the first ``<a>`` in the card
is the title/link and the card's text supplies location.

Playwright renders the page, then jobs are read from the DOM - first any
``JobPosting`` JSON-LD, otherwise a generic "job card" heuristic (every
anchor whose href contains ``/job`` plus the text of its container).
Cards rarely carry a posted date, so ``browser`` is a DATELESS source
and each run is capped at the first ``_MAX_CARDS`` results the page
shows; the not-seen sweep retires them.

Renders are serialised (``_SLOTS``) so discovery never launches more
than a couple of Chromium processes at once. If Playwright / Chromium
isn't installed the adapter simply returns [].
"""

from __future__ import annotations

import re
import threading

from ..normalize import clean_location, clean_title, parse_posted_at
from .base import DiscoveredJob

try:  # optional dependency - prod image installs it, tests/dev may not
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

_SLOTS = threading.Semaphore(2)
_MAX_CARDS = 25
_NAV_TIMEOUT = 45_000
_JOB_LINK = "a[href*='/job'], a[href*='JobDetail'], a[href*='job-detail']"

_LD_BLOCK = re.compile(
    r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', re.S | re.I
)
_DATE = re.compile(
    r"(?:posted[:\s]+)(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}"
    r"|\d+\+?\s+days?\s+ago|today|yesterday)",
    re.I,
)
# a "City, Region, Country" run that ends in a country/state token
_LOC = re.compile(
    r"([A-Z][A-Za-z.\-]+(?:[ /][A-Za-z.\-]+){0,3},\s*"
    r"(?:[A-Za-z][A-Za-z. \-]+,\s*)?"
    r"(?:India|IN|USA?|United States|United Kingdom|UK|Germany|Singapore|"
    r"China|CHN|Japan|JPN|Karnataka|Maharashtra|Telangana|Tamil Nadu|"
    r"Haryana|Uttar Pradesh|[A-Z]{2,3}))\b"
)


def _render_html(url: str) -> str | None:
    if sync_playwright is None:
        return None

    with _SLOTS:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/152.0.0.0 Safari/537.36"
                    )
                )
                try:
                    page.goto(
                        url, wait_until="domcontentloaded", timeout=_NAV_TIMEOUT
                    )
                    try:
                        page.wait_for_selector(_JOB_LINK, timeout=15_000)
                    except Exception:
                        pass
                    page.wait_for_timeout(2_000)
                    return page.content()
                finally:
                    browser.close()
        except Exception:
            return None


def _from_json_ld(html: str) -> list[DiscoveredJob]:
    import json

    jobs: list[DiscoveredJob] = []
    for block in _LD_BLOCK.findall(html):
        try:
            data = json.loads(block.strip())
        except ValueError:
            continue
        for item in data if isinstance(data, list) else [data]:
            if not isinstance(item, dict) or item.get("@type") != "JobPosting":
                continue
            loc = item.get("jobLocation")
            loc = loc[0] if isinstance(loc, list) and loc else loc
            addr = loc.get("address") if isinstance(loc, dict) else None
            where = None
            if isinstance(addr, dict):
                parts = []
                for key in ("addressLocality", "addressRegion", "addressCountry"):
                    v = addr.get(key)
                    if isinstance(v, dict):
                        v = v.get("name")
                    if isinstance(v, str) and v.strip():
                        parts.append(v)
                where = ", ".join(parts)
            url = item.get("url")
            jobs.append(
                DiscoveredJob(
                    company="",
                    external_job_id=str(item.get("identifier") or "") or None,
                    title=clean_title(item.get("title")),
                    location=clean_location(where),
                    job_url=url if isinstance(url, str) else None,
                    posted_at=parse_posted_at(item.get("datePosted")),
                    source="browser",
                )
            )
    return jobs


def _from_cards(html: str, base_hint: str) -> list[DiscoveredJob]:
    try:
        from bs4 import BeautifulSoup
    except ImportError:  # pragma: no cover
        return []

    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    jobs: list[DiscoveredJob] = []

    for anchor in soup.select(_JOB_LINK):
        href = anchor.get("href") or ""
        if not href or href in seen:
            continue
        title = clean_title(anchor.get_text(" "))
        if not title or len(title) > 140:
            continue
        seen.add(href)

        container = anchor
        for _ in range(4):
            if container.parent is None:
                break
            container = container.parent
            if container.name in ("li", "article", "tr"):
                break
        text = re.sub(r"\s+", " ", container.get_text(" ")).strip()

        loc_match = _LOC.search(text)
        date_match = _DATE.search(text)

        job_url = href if href.startswith("http") else base_hint.rstrip("/") + href
        jobs.append(
            DiscoveredJob(
                company="",
                external_job_id=re.sub(r"\W+", "", href)[-24:] or None,
                title=title,
                location=(
                    clean_location(loc_match.group(1)) if loc_match else None
                ),
                job_url=job_url,
                posted_at=(
                    parse_posted_at(date_match.group(0)) if date_match else None
                ),
                source="browser",
            )
        )
        if len(jobs) >= _MAX_CARDS:
            break

    return jobs


def _from_selector(
    html: str, card_sel: str, loc_sel: str, base: str
) -> list[DiscoveredJob]:
    try:
        from bs4 import BeautifulSoup
    except ImportError:  # pragma: no cover
        return []

    soup = BeautifulSoup(html, "html.parser")
    jobs: list[DiscoveredJob] = []

    for card in soup.select(card_sel):
        anchor = card.find("a", href=True)
        if anchor is None:
            continue
        title = clean_title(anchor.get_text(" "))
        if not title:
            continue
        href = anchor["href"]
        text = re.sub(r"\s+", " ", card.get_text(" ")).strip()

        location = None
        if loc_sel:
            el = card.select_one(loc_sel)
            if el is not None:
                location = clean_location(
                    re.sub(r"^\s*Location[:\s]+", "", el.get_text(" "), flags=re.I)
                )
        if not location:
            loc_match = _LOC.search(text)
            location = clean_location(loc_match.group(1)) if loc_match else None
        date_match = _DATE.search(text)

        jobs.append(
            DiscoveredJob(
                company="",
                external_job_id=re.sub(r"\W+", "", href)[-24:] or None,
                title=title,
                location=location,
                job_url=href if href.startswith("http") else base + href,
                posted_at=(
                    parse_posted_at(date_match.group(1)) if date_match else None
                ),
                source="browser",
            )
        )
        if len(jobs) >= _MAX_CARDS:
            break

    return jobs


def parse_jobs(html: str, token: str = "") -> list[DiscoveredJob]:
    if not html:
        return []
    parts = token.split("###")
    url = parts[0]
    card_sel = parts[1] if len(parts) > 1 else ""
    loc_sel = parts[2] if len(parts) > 2 else ""
    base_match = re.match(r"https?://[^/]+", url)
    base = base_match.group(0) if base_match else ""

    if card_sel:
        return _from_selector(html, card_sel, loc_sel, base)

    jobs = _from_json_ld(html)
    if jobs:
        return jobs[:_MAX_CARDS]
    return _from_cards(html, base)


class BrowserSource:
    name = "browser"

    def discover(self, token: str) -> list[DiscoveredJob]:
        if not token.startswith("http"):
            return []
        url = token.split("###", 1)[0]
        return parse_jobs(_render_html(url), token)
