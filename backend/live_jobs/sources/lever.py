"""Lever public postings API.

    https://api.lever.co/v0/postings/{token}?mode=json

Unauthenticated. Returns a JSON array. `token` is the Lever site slug
(e.g. "matchgroup"). `createdAt` is epoch milliseconds.
"""

from __future__ import annotations

from ..normalize import (
    clean_description,
    clean_location,
    clean_title,
    parse_posted_at,
)
from .base import DiscoveredJob, get_json

URL = "https://api.lever.co/v0/postings/{token}"


def parse_jobs(payload: object) -> list[DiscoveredJob]:
    if not isinstance(payload, list):
        return []

    jobs: list[DiscoveredJob] = []

    for item in payload:
        if not isinstance(item, dict):
            continue

        categories = item.get("categories") or {}

        # the list feed carries the full ad already - plain text if
        # present, else the HTML body, plus the "lists" (Requirements
        # etc.) which is usually where the experience line lives.
        list_text = " ".join(
            f"{block.get('text', '')} {block.get('content', '')}"
            for block in (item.get("lists") or [])
            if isinstance(block, dict)
        )
        description = (
            f"{item.get('descriptionPlain') or item.get('description') or ''} "
            f"{list_text}"
        )

        jobs.append(
            DiscoveredJob(
                company="",
                external_job_id=item.get("id"),
                title=clean_title(item.get("text")),
                location=clean_location(categories.get("location")),
                job_url=item.get("hostedUrl"),
                posted_at=parse_posted_at(item.get("createdAt")),
                description=clean_description(description),
                source="lever",
            )
        )

    return jobs


class LeverSource:
    name = "lever"

    def discover(self, token: str) -> list[DiscoveredJob]:
        data = get_json(URL.format(token=token), params={"mode": "json"})
        return parse_jobs(data)
