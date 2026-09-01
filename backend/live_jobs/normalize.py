"""Pure helpers shared by the source adapters and the discovery pipeline.

No DB, no network. Mirrors the spirit of main.normalize / main.parse_received
but kept separate so importing this never drags in the FastAPI app.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

_WS = re.compile(r"\s+")
_TAG = re.compile(r"<[^>]+>")
_EPOCH = re.compile(r"\d{10,13}")

_DATE_FORMATS = ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y", "%d %B %Y")


def clean_title(value: str | None) -> str:
    if not value:
        return ""
    return _WS.sub(" ", _TAG.sub(" ", value)).strip()


def clean_location(value: str | None) -> str | None:
    if not value:
        return None
    text = _WS.sub(" ", _TAG.sub(" ", value)).strip(" ,;|-")
    return text or None


def normalize_company(value: str | None) -> str:
    """Lowercase, alphanumeric-only key for matching."""
    if not value:
        return ""
    text = re.sub(r"[^a-z0-9]+", " ", str(value).lower())
    return _WS.sub(" ", text).strip()


def parse_posted_at(value: object) -> datetime | None:
    """Best-effort parse into a naive UTC datetime.

    Accepts ISO 8601, RFC 2822, epoch seconds / milliseconds (int, float
    or numeric string), and a few human date formats. Returns None if
    nothing parses - discovery drops jobs with no real posted date.
    """
    if value is None or value == "":
        return None

    if isinstance(value, (int, float)) or (
        isinstance(value, str) and _EPOCH.fullmatch(value.strip())
    ):
        seconds = float(value)
        if seconds > 1e11:  # milliseconds (Lever)
            seconds /= 1000.0
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(
                tzinfo=None
            )
        except (OverflowError, OSError, ValueError):
            return None

    text = _WS.sub(" ", str(value).strip())

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return _to_naive_utc(parsed)
    except ValueError:
        pass

    try:
        parsed = parsedate_to_datetime(text)
        if parsed is not None:
            return _to_naive_utc(parsed)
    except (TypeError, ValueError):
        pass

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    return None


def _to_naive_utc(parsed: datetime) -> datetime:
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def fallback_external_id(
    company: str,
    title: str,
    location: str | None,
    url: str | None,
) -> str:
    """Deterministic id for sources that don't supply one, so a re-sync
    updates the same row instead of inserting a duplicate every time."""
    basis = "|".join(
        [
            normalize_company(company),
            clean_title(title).lower(),
            (location or "").strip().lower(),
            (url or "").split("?")[0].strip().lower(),
        ]
    )
    return "fb_" + hashlib.sha1(basis.encode("utf-8")).hexdigest()[:20]
