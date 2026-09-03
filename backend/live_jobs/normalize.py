"""Pure helpers shared by the source adapters and the discovery pipeline.

No DB, no network. Mirrors the spirit of main.normalize / main.parse_received
but kept separate so importing this never drags in the FastAPI app.
"""

from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

_WS = re.compile(r"\s+")
_TAG = re.compile(r"<[^>]+>")
_EPOCH = re.compile(r"\d{10,13}")
# Workday-style relative strings: "Posted Today", "Posted Yesterday",
# "Posted 5 Days Ago", "Posted 30+ Days Ago".
_RELATIVE = re.compile(
    r"posted\s+(today|yesterday|(\d+)\+?\s+days?\s+ago)", re.IGNORECASE
)

_DATE_FORMATS = (
    "%B %d, %Y",
    "%b %d, %Y",
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%d %B %Y",
    "%d %b %Y",
)


def clean_title(value: str | None) -> str:
    if not value:
        return ""
    return _WS.sub(" ", _TAG.sub(" ", value)).strip()


def clean_location(value: str | None) -> str | None:
    if not value:
        return None
    text = _WS.sub(" ", _TAG.sub(" ", value)).strip(" ,;|-")
    return text or None


def clean_description(value: str | None, max_len: int = 4000) -> str | None:
    """Strip HTML, collapse whitespace, cap length. Job ad bodies come
    through as HTML from most feeds and we only keep them to parse an
    experience requirement out, so a few KB is plenty."""
    if not value:
        return None
    unescaped = html.unescape(str(value))
    text = _WS.sub(" ", _TAG.sub(" ", unescaped)).strip()
    if not text:
        return None
    return text[:max_len]


# Experience requirement, e.g. "5+ years", "3-5 years of experience",
# "minimum 8 years". Deliberately conservative - a bare "2 years" only
# counts when "experience" follows soon after, so "2 years ago" / "a
# 4 year degree" don't register.
_EXP_RANGE = re.compile(
    r"(?<!\d)(\d{1,2})\s*\+?\s*(?:-|–|—|to)\s*(\d{1,2})(?!\d)\s*\+?\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)
_EXP_MIN = re.compile(
    r"(?<!\d)(\d{1,2})(?!\d)\s*\+\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)
_EXP_PLAIN = re.compile(
    r"(?<!\d)(\d{1,2})(?!\d)\s*(?:years?|yrs?)(?:['’]?)\s*"
    r"(?:of\s+)?(?:[a-z]+\s+){0,3}experience",
    re.IGNORECASE,
)


def parse_experience(text: str | None) -> tuple[int | None, int | None]:
    """(min_years, max_years) parsed from a title + description blob.

    ``(3, 5)`` for a range, ``(5, None)`` for "5+ years" or a lone
    "5 years experience", ``(None, None)`` when nothing usable is found.
    """
    if not text:
        return (None, None)

    def _ok(*values: int) -> bool:
        return all(0 <= v <= 40 for v in values)

    match = _EXP_RANGE.search(text)
    if match:
        lo, hi = int(match.group(1)), int(match.group(2))
        if _ok(lo, hi) and lo <= hi:
            return (lo, hi)

    match = _EXP_MIN.search(text)
    if match:
        lo = int(match.group(1))
        if _ok(lo):
            return (lo, None)

    match = _EXP_PLAIN.search(text)
    if match:
        lo = int(match.group(1))
        if _ok(lo):
            return (lo, None)

    return (None, None)


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

    relative = _RELATIVE.search(text)
    if relative:
        token = relative.group(1).lower()
        if "today" in token:
            days = 0
        elif "yesterday" in token:
            days = 1
        else:
            days = int(relative.group(2))
        midnight = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return midnight - timedelta(days=days)

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
