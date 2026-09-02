"""Google careers - the internal ``batchexecute`` RPC the results page calls.

    POST https://www.google.com/about/careers/applications/_/
         HiringCportalFrontendUi/data/batchexecute?rpcids=r06xKb&...
        f.req = [[["r06xKb","[[null,null,null,null,\"en-GB\",null,null,<page>]]",
                   null,"3"]]]

Unauthenticated - no ``at`` token or cookies needed. Google soft-blocks
bursts hard: after a few quick calls the RPC answers HTTP 200 with an
empty ``[["e",4,...]]`` frame for many minutes, so discovery runs this
on its slowest cadence (see ``GUARDED_SOURCES``) and never paginates in
a tight loop.

The response is the ``)]}'``-prefixed, length-delimited protojson Wiz
uses. Each job in the decoded payload is roughly::

    [ job_id, title, apply_url,
      [_, responsibilities_html], [_, qualifications_html], ... ]

Location and any post date live further along that array and are not yet
mapped - until they are, Google is treated as a DATELESS source and the
rough location comes from the ``loc=`` param on the apply URL.
``token`` is unused (per-company adapter).
"""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import requests

from ..normalize import clean_location, clean_title
from .base import DiscoveredJob

RPC = "r06xKb"
URL = (
    "https://www.google.com/about/careers/applications/_/"
    "HiringCportalFrontendUi/data/batchexecute"
)
_PARAMS = {
    "rpcids": RPC,
    "source-path": "/about/careers/applications/jobs/results",
    "bl": "boq_corp-hiring-boq-cportal-frontend_20260831.03_p0",
    "hl": "en-GB",
    "soc-app": "1",
    "soc-platform": "1",
    "soc-device": "1",
    "rt": "c",
}
_TIMEOUT = (5, 20)
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    "X-Same-Domain": "1",
    "Origin": "https://www.google.com",
    "Referer": "https://www.google.com/about/careers/applications/jobs/results",
}
_FRAME_KEY = f'["wrb.fr","{RPC}",'


def _inner(page: int) -> str:
    return json.dumps([[None, None, None, None, "en-GB", None, None, page]])


def _decode(text: str) -> object | None:
    """Pull the r06xKb payload out of the ``)]}'``-prefixed protojson body.

    The response is length-delimited chunks of JSON, but the framing is
    fiddly and the useful bit is always one ``wrb.fr`` row whose third
    element is a JSON string. Locate that row and decode just the string
    - a soft-blocked response has ``null`` there instead and yields None.
    """
    start = text.find(_FRAME_KEY)
    if start < 0:
        return None

    try:
        value, _ = json.JSONDecoder().raw_decode(text, start + len(_FRAME_KEY))
    except ValueError:
        return None

    if not isinstance(value, str):
        return None

    try:
        return json.loads(value)
    except ValueError:
        return None


def _location_from_url(url: str) -> str | None:
    try:
        loc = parse_qs(urlparse(url).query).get("loc", [None])[0]
    except ValueError:
        loc = None
    return clean_location(loc)


def parse_jobs(payload: object) -> list[DiscoveredJob]:
    listings = payload[0] if isinstance(payload, list) and payload else None
    if not isinstance(listings, list):
        return []

    jobs: list[DiscoveredJob] = []

    for item in listings:
        if not isinstance(item, list) or len(item) < 3:
            continue

        job_id, title, url = item[0], item[1], item[2]
        if not job_id or not isinstance(title, str):
            continue

        jobs.append(
            DiscoveredJob(
                company="Google",
                external_job_id=str(job_id),
                title=clean_title(title),
                location=_location_from_url(url) if isinstance(url, str) else None,
                job_url=url if isinstance(url, str) else None,
                posted_at=None,  # date field not yet mapped - DATELESS
                source="google",
            )
        )

    return jobs


class GoogleSource:
    name = "google"

    def discover(self, token: str = "") -> list[DiscoveredJob]:
        freq = json.dumps([[[RPC, _inner(1), None, "3"]]])
        try:
            response = requests.post(
                URL,
                params={**_PARAMS, "_reqid": "100000"},
                data={"f.req": freq},
                headers=_HEADERS,
                timeout=_TIMEOUT,
            )
        except requests.RequestException:
            return []

        if response.status_code != 200:
            return []

        return parse_jobs(_decode(response.text))
