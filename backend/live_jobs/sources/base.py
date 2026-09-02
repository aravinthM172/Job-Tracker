"""Common types + HTTP helper for Live Jobs source adapters.

A source adapter turns one company's public careers feed (the same
unauthenticated JSON endpoint the company's own careers page calls) into
a list of DiscoveredJob. Adapters must never raise into the discovery
loop - on any network or parse error they return an empty list.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

import requests

# (connect, read) - a slow-trickling response shouldn't stall a whole
# sync, and one dead company shouldn't hold up the other ~20.
_TIMEOUT = (5, 20)
_HEADERS = {
    "User-Agent": "job-application-tracker/1.0 (personal use)",
    "Accept": "application/json",
}


@dataclass
class DiscoveredJob:
    company: str
    external_job_id: str | None
    title: str
    location: str | None
    job_url: str | None
    posted_at: datetime | None
    description: str | None = None
    source: str = "unknown"


@runtime_checkable
class JobSource(Protocol):
    name: str

    def discover(self, token: str) -> list[DiscoveredJob]:
        ...


def get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: Any | None = None,
    method: str = "GET",
) -> Any | None:
    """GET/POST a URL and return parsed JSON, or None on any failure."""
    try:
        response = requests.request(
            "POST" if json_body is not None else method,
            url,
            params=params,
            json=json_body,
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    try:
        return response.json()
    except ValueError:
        return None


def get_text(url: str, *, params: dict[str, Any] | None = None) -> str | None:
    """GET a URL and return the response body, or None on any failure."""
    try:
        response = requests.get(
            url, params=params, headers=_HEADERS, timeout=_TIMEOUT
        )
    except requests.RequestException:
        return None
    if response.status_code != 200:
        return None
    return response.text
