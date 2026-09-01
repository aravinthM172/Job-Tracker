from live_jobs.discovery import discover_all_companies
from live_jobs.routes import router as live_jobs_router
import sys

# Windows consoles default to cp1252, which can't print emoji that show up
# in real email subjects (e.g. "⭐") - unhandled, that crash bubbles out of
# scan_gmail/scan_outlook's print() calls and kills the whole account sync.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import base64
import html as html_entities
import json
import os
import re
import requests
import secrets
import threading
import time
import traceback

from bs4 import BeautifulSoup
from sqlalchemy import func

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials as GoogleCredentials

from db import SessionLocal, Job, JobEvent, STATUS_PRIORITY
from microsoft_auth import get_login_url, get_token, refresh_access_token

# ============================================================
# APP
# ============================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    # _background_sync_loop is defined further down (with the rest of
    # the sync machinery) - fine, since this only runs after the
    # whole module has finished loading.
    threading.Thread(target=_background_sync_loop, daemon=True).start()

    print(
        f"[AUTO-SYNC] background sync enabled - "
        f"every {AUTO_SYNC_INTERVAL_SECONDS // 60} minutes"
    )

    yield


app = FastAPI(title="Job Application Tracker", lifespan=lifespan)


app.include_router(live_jobs_router)

app.add_middleware(
    CORSMiddleware,
    # Regex (not a fixed allow_origins list) so the dashboard also
    # works over Tailscale - its device IP (100.64.0.0/10 CGNAT
    # range) and MagicDNS hostname (*.ts.net) aren't known ahead of
    # time the way localhost is.
    allow_origin_regex=(
        r"^http://("
        r"localhost"
        r"|127\.0\.0\.1"
        r"|100\.\d{1,3}\.\d{1,3}\.\d{1,3}"
        r"|[\w-]+\.[\w-]+\.ts\.net"
        r"):5173$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# HTTP Basic Auth gate in front of the whole app - this holds job
# search emails/companies and a public /sync trigger, so a deployment
# reachable on the open internet (unlike localhost/Tailscale-only use)
# needs *something* in front of it. No-ops when BASIC_AUTH_USER/PASS
# aren't set (local dev, Tailscale-only use) so neither is ever
# required to run the app locally.
BASIC_AUTH_USER = os.getenv("BASIC_AUTH_USER")
BASIC_AUTH_PASS = os.getenv("BASIC_AUTH_PASS")


@app.middleware("http")
async def basic_auth(request: Request, call_next):
    if not BASIC_AUTH_USER or not BASIC_AUTH_PASS:
        return await call_next(request)

    auth_header = request.headers.get("authorization", "")
    scheme, _, credentials = auth_header.partition(" ")

    if scheme.lower() == "basic":
        try:
            decoded = base64.b64decode(credentials).decode("utf-8")
            user, _, password = decoded.partition(":")
        except Exception:
            user, password = "", ""

        if secrets.compare_digest(user, BASIC_AUTH_USER) and secrets.compare_digest(
            password, BASIC_AUTH_PASS
        ):
            return await call_next(request)

    return Response(
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="Job Tracker"'},
    )

BASE_DIR = Path(__file__).resolve().parent
# Same DATA_DIR as db.py (see db.py) - keeps OAuth tokens on the same
# persistent volume as the DB in a deployed container.
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR)))
TOKEN_DIR = DATA_DIR / "tokens"
TOKEN_DIR.mkdir(parents=True, exist_ok=True)

OUTLOOK_TOKEN = TOKEN_DIR / "outlook_1.json"

GMAIL_FILES = [
    TOKEN_DIR / "gmail_1.json",
    TOKEN_DIR / "gmail_2.json",
    TOKEN_DIR / "gmail_3.json",
    TOKEN_DIR / "gmail_4.json",
]

GRAPH_URL = "https://graph.microsoft.com/v1.0"
GMAIL_URL = "https://gmail.googleapis.com/gmail/v1/users/me"

# How far back each sync scans, across every Gmail + Outlook account.
SYNC_WINDOW_DAYS = 30

# ============================================================
# ACCOUNT SYNC STATE (in-memory, filled in by the most recent /sync run)
# ============================================================

ACCOUNT_STATE = {}


# ============================================================
# MODELS
# ============================================================

class JobCreate(BaseModel):
    company: str
    role: str
    job_id: str = ""
    applied_date: str


# ============================================================
# HELPERS
# ============================================================

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path):
    try:
        if not path.exists():
            return None

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        print(f"[ERROR] Cannot read {path}: {e}")
        return None


def normalize(value):
    if not value:
        return ""

    value = str(value).lower()

    value = re.sub(r"[^a-z0-9]+", " ", value)

    return re.sub(r"\s+", " ", value).strip()


def parse_received(value):
    """Best-effort parse of an email's received timestamp into a
    timezone-naive UTC datetime. Gmail sends RFC2822 strings, Outlook
    sends ISO 8601. Falls back to "now" so a bad/missing date never
    breaks a sync."""

    if not value:
        return datetime.utcnow()

    try:
        return (
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            .astimezone(timezone.utc)
            .replace(tzinfo=None)
        )
    except Exception:
        pass

    try:
        parsed = parsedate_to_datetime(value)

        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)

        return parsed
    except Exception:
        return datetime.utcnow()


# ============================================================
# EMAIL CLASSIFICATION
# ============================================================

APPLICATION_PATTERNS = [
    r"\bapplication received\b",
    r"\bapplication submitted\b",
    r"\bapplication has been received\b",
    r"\bwe received your application\b",
    r"\bthanks for applying\b",
    r"\bthank you for applying\b",
    r"\bthank you for your application\b",
    r"\bsuccessfully applied\b",
    r"\byour application for\b",
    r"\bapplication confirmation\b",
    r"\bconfirmed your application\b",
    r"\breceived your application\b",
    r"\bhas received your application\b",
    r"\bresume received\b",
    r"\byour resume has been received\b",
]

ASSESSMENT_PATTERNS = [
    r"\bassessment\b",
    r"\bcoding assessment\b",
    r"\btechnical assessment\b",
    r"\btest invitation\b",
    r"\bcomplete the assessment\b",
]

INTERVIEW_PATTERNS = [
    r"\binterview invitation\b",
    r"\binterview invite\b",
    r"\bschedule an interview\b",
    r"\bnext round\b",
    r"\bphone screen\b",
    r"\btechnical round\b",
]

# The bare word "interview" is only checked against the SUBJECT, not
# the body - almost every application-acknowledgment email mentions
# "interview" somewhere in its boilerplate ("if you are selected for
# an interview...", "reach out if you are moved forward in the
# interview journey...") without one actually being offered. A real
# invite puts "interview" in the subject line itself; a hypothetical
# future-process mention buried in body text does not.
INTERVIEW_SUBJECT_ONLY_PATTERNS = [
    r"\binterview\b",
]

REJECTION_PATTERNS = [
    r"\bapplication.*unsuccessful\b",
    r"\bnot moving forward\b",
    r"\bwe will not be moving forward\b",
    r"\bregret to inform\b",
    r"\bnot selected\b",
    r"\bnot been selected\b",
    r"\bapplication.*rejected\b",
    r"\bposition.*filled\b",
    r"\bdecided to pursue other candidates\b",
    r"\bwill not be proceeding\b",
    r"\bdecided not to proceed\b",
    r"\bnot to proceed with your\b",
]

OFFER_PATTERNS = [
    r"\bjob offer\b",
    r"\boffer letter\b",
    r"\bpleased to offer\b",
    r"\boffer of employment\b",
    r"\bwe are delighted to offer\b",
]

# Legal disclaimer boilerplate some ATSes (e.g. Wells Fargo/Workday)
# append to every plain "we received your application" email - e.g.
# "This email is not an offer of employment." Without this guard,
# OFFER_PATTERNS' "offer of employment" match fires on the negation
# and misclassifies a routine application-received email as an offer.
OFFER_NEGATION_PATTERNS = [
    r"\bnot (?:an? )?(?:formal )?offer of employment\b",
    r"\bdoes not constitute (?:an? )?(?:formal )?offer\b",
]


def contains_pattern(text, patterns):
    text = normalize(text)

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def classify_email(subject="", body=""):
    text = f"{subject} {body}"

    # Highest priority first
    if contains_pattern(text, OFFER_PATTERNS) and not contains_pattern(
        text, OFFER_NEGATION_PATTERNS
    ):
        return "offer"

    if contains_pattern(text, REJECTION_PATTERNS):
        return "rejected"

    if contains_pattern(text, INTERVIEW_PATTERNS):
        return "interview"

    if contains_pattern(subject, INTERVIEW_SUBJECT_ONLY_PATTERNS):
        return "interview"

    if contains_pattern(text, ASSESSMENT_PATTERNS):
        return "assessment"

    if contains_pattern(text, APPLICATION_PATTERNS):
        return "application_received"

    return None


# ============================================================
# IGNORE JOB ALERT / MARKETING EMAILS
# ============================================================

IGNORE_PATTERNS = [
    r"\bnew openings\b",
    r"\bjob openings\b",
    r"\btop jobs for you\b",
    r"\bjobs for you\b",
    r"\bjobs you may like\b",
    r"\bjob alert\b",
    r"\bjob alerts\b",
    r"\brecommended jobs\b",
    r"\brecommendations\b",
    r"\bweekly jobs\b",
    r"\bcareer opportunities\b",
    r"\bnewsletter\b",
    # NOT "\bunsubscribe\b" - it's only safe against the short
    # bodyPreview snippet (never actually reaches the sign-off footer
    # where every modern email, including genuine ones, has an
    # unsubscribe link for compliance); dropped so it can't silently
    # start blocking real emails if this ever runs against full body
    # text instead.
    r"\bjobs based on your profile\b",
    r"\bnew opportunities\b",
    # Job-alert digests and interview-prep marketing content that
    # happen to contain "interview"/"assessment" but aren't a real
    # invite - seen matching false-positive "interview" events in
    # practice (e.g. "New jobs: ... and 6 more", "Top Questions &
    # Answers", "see what employees have to say").
    r"\bnew jobs\b",
    r"\btop questions\b",
    r"\bwhat employees have to say\b",
    r"\binterview questions\b",
    r"\binterview tips\b",
    r"\bhow to (?:ace|prepare for)\b",
    # AI interview-copilot ad ("Make ParakeetAI answers sound like you")
    r"\bparakeetai\b",
    # Mass recruitment-marketplace blasts ("Walk-in invite from
    # recruiter... you've been chosen from a large pool of
    # jobseekers") - a generic outreach template, not a real
    # personal interview invite, despite the subject often literally
    # saying "walk-in interview".
    r"\bchosen from a large pool\b",
    r"\bwalk-?in invite\b",
]

# normalize() strips everything but a-z0-9, so non-Latin-script
# newsletters (e.g. Cyrillic interview-prep content) never reach the
# IGNORE_PATTERNS word-boundary regexes above - checked separately
# against the raw text instead.
RAW_IGNORE_SUBSTRINGS = [
    "спросят на интервью",  # Russian: "[what they] ask at interview" - interview-prep newsletter, not a real invite
]

# Senders whose "application"-shaped emails are actually marketing,
# not a real job application - confirmed against this account's data:
# Talent500 sells "unlock interviews" registration/urgency emails,
# and CodingNinjas' course/bootcamp enrollment flow uses the exact
# same "confirm your application" wording as a real job application.
AD_SENDER_DOMAINS = (
    "talent500.co",
    "codingninjas.com",
)


def is_generic_job_alert(subject, body, sender=""):
    text = f"{subject} {body}"

    if any(s in text.lower() for s in RAW_IGNORE_SUBSTRINGS):
        return True

    domain = sender_domain(sender)

    if any(
        domain == d or domain.endswith("." + d)
        for d in AD_SENDER_DOMAINS
    ):
        return True

    return contains_pattern(text, IGNORE_PATTERNS)


# ============================================================
# ROLE EXTRACTION
# ============================================================

ROLE_PATTERNS = [
    r"applying to\s+(.+?)(?:\s+at\s|\s+with\s|!|\.|$)",
    r"applying for\s+(.+?)(?:\s+at\s|\s+with\s|!|\.|$)",
    r"application for\s+(?:the\s+)?(.+?)(?:\s+at\s|\s+with\s|!|\.|$)",
    r"your application for\s+(?:the\s+)?(.+?)(?:\s+at\s|\s+with\s|!|\.|$)",
    r"for the position of\s+(.+?)(?:\s+at\s|!|\.|$)",
    r"position:\s*(.+?)(?:\.|!|$)",
    r"role:\s*(.+?)(?:\.|!|$)",
]

ROLE_KEYWORDS = [
    "software development engineer",
    "software engineer",
    "software developer",
    "machine learning engineer",
    "data engineer",
    "data scientist",
    "data analyst",
    "business analyst",
    "ai engineer",
    "product analyst",
    "cloud engineer",
    "devops engineer",
    "support engineer",
    "technical support",
    "data science",
    "operations analyst",
]


def guess_role(subject, body=""):
    text = f"{subject} {body}".strip()

    for pattern in ROLE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            value = match.group(1).strip(" -:")

            if 3 <= len(value) <= 120:
                return value.title()

    lower = text.lower()

    for role in sorted(ROLE_KEYWORDS, key=len, reverse=True):
        if role in lower:
            return role.title()

    return "Unknown Role"


# ============================================================
# GMAIL
# ============================================================

def get_gmail_token(path):
    data = load_json(path)

    if not data:
        return None

    token = data.get("token")

    if isinstance(token, dict):
        access_token = token.get("access_token") or token.get("token")

    else:
        access_token = token

        # These files are google-auth's Credentials.to_json() output
        # (see email_sync.py's gmail_login): refresh_token/client_id/
        # token_uri are right there alongside the access token. Gmail
        # access tokens last ~1hr, so without this a sync that runs
        # long (a high-volume mailbox) or starts a while after login
        # fails every request with 401 instead of just refreshing.
        if data.get("refresh_token") and data.get("client_id"):
            try:
                creds = GoogleCredentials.from_authorized_user_info(
                    data,
                    data.get("scopes"),
                )

                if creds.expired and creds.refresh_token:
                    creds.refresh(GoogleAuthRequest())

                    path.write_text(creds.to_json(), encoding="utf-8")

                    access_token = creds.token

            except Exception as e:
                print(f"[GMAIL] {path.name}: token refresh failed: {e}")

    if not access_token:
        return None

    return access_token


def gmail_headers(token):
    return {
        "Authorization": f"Bearer {token}"
    }


# Zero-width space (U+200B), zero-width non-joiner (U+200C),
# zero-width joiner (U+200D), BOM (U+FEFF), figure space (U+2007) -
# marketing emails often pack hundreds of these into a hidden
# preheader, and they leak into the extracted plain text as
# invisible garbage.
INVISIBLE_CHARS = re.compile("[​‌‍﻿ ]")


def clean_body_text(text):
    if not text:
        return ""

    # Some senders' plain-text part is poorly generated and contains
    # literal HTML entities (&nbsp;, &amp;) instead of real characters.
    text = html_entities.unescape(text)

    text = INVISIBLE_CHARS.sub("", text)

    return re.sub(r"\n{3,}", "\n\n", text).strip()


def strip_html(html):
    if not html:
        return ""

    try:
        text = BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
    except Exception:
        text = re.sub(r"<[^>]+>", " ", html)

    return clean_body_text(text)


def gmail_extract_body(payload):
    """Walk a Gmail "full"-format payload for the message text,
    preferring text/plain and falling back to text/html (stripped)."""

    plain = ""
    html = ""

    def walk(part):
        nonlocal plain, html

        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data")

        if data and mime == "text/plain" and not plain:
            try:
                plain = base64.urlsafe_b64decode(
                    data + "=="
                ).decode("utf-8", errors="ignore")
            except Exception:
                pass

        elif data and mime == "text/html" and not html:
            try:
                html = base64.urlsafe_b64decode(
                    data + "=="
                ).decode("utf-8", errors="ignore")
            except Exception:
                pass

        for sub in part.get("parts", []):
            walk(sub)

    walk(payload)

    body = clean_body_text(plain) or strip_html(html)

    # Full email bodies can run to tens of KB (tracking pixels, long
    # HTML boilerplate) - cap what gets stored, no UI needs more.
    return body[:20000]


def gmail_get_message(session, token, message_id):
    try:
        r = session.get(
            f"{GMAIL_URL}/messages/{message_id}",
            headers=gmail_headers(token),
            params={
                "format": "full",
            },
            # (connect, read) tuple - a plain float only bounds each
            # individual socket read, so a connection trickling data
            # slowly (rare, but seen mid-scan) can stall well past 15s
            # without ever raising. This bounds it properly.
            timeout=(5, 15),
        )

        if r.status_code != 200:
            return None

        data = r.json()

        payload = data.get("payload", {})

        headers = {}

        for h in payload.get("headers", []):
            headers[h.get("name", "").lower()] = h.get("value", "")

        return {
            "id": data.get("id"),
            "threadId": data.get("threadId"),
            "subject": headers.get("subject", ""),
            "from": headers.get("from", ""),
            "received": headers.get("date", ""),
            "bodyPreview": data.get("snippet", ""),
            "body": gmail_extract_body(payload),
            "webLink": (
                f"https://mail.google.com/mail/u/0/#all/{data.get('id')}"
            ),
        }

    except Exception as e:
        print(f"[GMAIL MESSAGE ERROR] {e}")
        return None


def scan_gmail(account_name, path, max_messages=500, since=None):
    """Returns (emails, error). error is None on success (even if 0
    relevant emails were found) so callers can tell "nothing relevant"
    apart from "the account is broken".

    Scans every message received since `since` (paginating through
    Gmail's list endpoint), not just the most recent page. `since`
    defaults to SYNC_WINDOW_DAYS ago for an account's first-ever sync;
    every sync after that only looks at what's new, instead of
    re-fetching (and re-downloading the full body of) the same
    thousand messages every single time."""

    print(f"[GMAIL] {account_name}: starting")

    token = get_gmail_token(path)

    if not token:
        print(f"[GMAIL] {account_name}: token missing")
        return [], "No token found. Authenticate this Gmail account."

    if since is None:
        since = datetime.utcnow() - timedelta(days=SYNC_WINDOW_DAYS)

    # -in:sent excludes the user's own outgoing mail - without it, a
    # follow-up/inquiry the user wrote themselves (which naturally
    # uses the same "application"/"interview" vocabulary) gets synced
    # as if it were a reply from the employer.
    query = f"after:{int(since.timestamp())} -in:sent"

    try:
        # A shared session keeps the underlying TCP/TLS connection to
        # Gmail alive across all requests for this account, instead of
        # renegotiating TLS for every single message (which is what
        # made a 500-message account take tens of minutes).
        with requests.Session() as session:

            message_ids = []
            page_token = None

            while len(message_ids) < max_messages:

                params = {
                    "maxResults": min(500, max_messages - len(message_ids)),
                    "q": query,
                }

                if page_token:
                    params["pageToken"] = page_token

                r = session.get(
                    f"{GMAIL_URL}/messages",
                    headers=gmail_headers(token),
                    params=params,
                    timeout=20,
                )

                if r.status_code == 401:
                    return [], "Token expired or invalid (401). Re-authenticate."

                if r.status_code != 200:
                    message = f"HTTP {r.status_code}: {r.text[:300]}"

                    print(f"[GMAIL] {account_name}: {message}")

                    return [], message

                data = r.json()

                message_ids.extend(
                    x.get("id")
                    for x in data.get("messages", [])
                    if x.get("id")
                )

                page_token = data.get("nextPageToken")

                if not page_token:
                    break

            print(
                f"[GMAIL] {account_name}: "
                f"{len(message_ids)} messages found since "
                f"{since.strftime('%Y-%m-%d %H:%M')} UTC"
            )

            results = []

            for index, message_id in enumerate(message_ids, start=1):

                if index % 100 == 0:
                    print(
                        f"[GMAIL] {account_name}: "
                        f"processed {index}/{len(message_ids)}"
                    )

                message = gmail_get_message(session, token, message_id)

                if not message:
                    continue

                event = classify_email(
                    message.get("subject", ""),
                    message.get("bodyPreview", "")
                )

                if not event:
                    continue

                if is_generic_job_alert(
                    message.get("subject", ""),
                    message.get("bodyPreview", ""),
                    message.get("from", ""),
                ):
                    continue

                message["_type"] = event
                message["_account"] = account_name

                results.append(message)

                print(
                    f"[GMAIL] {account_name}: "
                    f"MATCH [{event}] "
                    f"{message.get('subject', '')[:80]}"
                )

            print(
                f"[GMAIL] {account_name}: "
                f"{len(results)} relevant application emails"
            )

            return results, None

    except requests.Timeout:
        print(f"[GMAIL] {account_name}: TIMEOUT")
        return [], "Request timed out."

    except Exception as e:
        print(f"[GMAIL] {account_name}: ERROR {e}")
        return [], str(e)


# ============================================================
# OUTLOOK
# ============================================================

def get_outlook_token():
    data = load_json(OUTLOOK_TOKEN)

    if not data:
        return None

    token = data.get("token", {})

    if isinstance(token, dict):
        return token.get("access_token")

    return data.get("access_token")


def refresh_outlook_token():
    """Exchange the stored refresh_token for a new access token and
    persist it. This raw device-flow token blob has no absolute expiry
    timestamp saved (only a relative expires_in), so unlike Gmail we
    can't reliably check expiry up front - refresh reactively on 401
    instead."""

    data = load_json(OUTLOOK_TOKEN)

    if not data:
        return None

    token = data.get("token", {})

    refresh_token = (
        token.get("refresh_token")
        if isinstance(token, dict)
        else None
    )

    if not refresh_token:
        return None

    try:
        new_token = refresh_access_token(refresh_token)

    except Exception as e:
        print(f"[OUTLOOK] token refresh failed: {e}")
        return None

    data["token"] = new_token

    OUTLOOK_TOKEN.write_text(json.dumps(data), encoding="utf-8")

    return new_token.get("access_token")


def scan_outlook(max_messages=500, since=None):
    """Returns (emails, error), mirroring scan_gmail().

    Scans every message received since `since` (defaulting to
    SYNC_WINDOW_DAYS ago for a first-ever sync), following
    @odata.nextLink until exhausted or max_messages is hit."""

    print("[OUTLOOK] starting")

    token = get_outlook_token()

    if not token:
        print("[OUTLOOK] token missing")
        return [], "No token found. Authenticate the Outlook account."

    if since is None:
        since = datetime.utcnow() - timedelta(days=SYNC_WINDOW_DAYS)

    cutoff = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        messages = []

        # Restricted to Inbox specifically - /me/messages unscoped
        # spans the whole mailbox including Sent Items, which is how
        # the user's own outgoing replies/inquiries were getting
        # synced as if they were messages from an employer.
        endpoint = f"{GRAPH_URL}/me/mailFolders/inbox/messages"
        params = {
            "$top": min(100, max_messages),
            "$select": (
                "id,subject,from,receivedDateTime,"
                "bodyPreview,webLink,body"
            ),
            "$filter": f"receivedDateTime ge {cutoff}",
            "$orderby": "receivedDateTime desc",
        }

        with requests.Session() as session:

            while endpoint and len(messages) < max_messages:

                r = session.get(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {token}"
                    },
                    params=params,
                    timeout=30,
                )

                if r.status_code == 401:
                    print("[OUTLOOK] access token expired, refreshing...")

                    token = refresh_outlook_token()

                    if not token:
                        return [], (
                            "Token expired and refresh failed. "
                            "Re-authenticate."
                        )

                    r = session.get(
                        endpoint,
                        headers={
                            "Authorization": f"Bearer {token}"
                        },
                        params=params,
                        timeout=30,
                    )

                    if r.status_code == 401:
                        return [], (
                            "Token expired or invalid (401) even "
                            "after refresh. Re-authenticate."
                        )

                if r.status_code != 200:
                    message = f"HTTP {r.status_code}: {r.text[:500]}"

                    print(f"[OUTLOOK] {message}")

                    return [], message

                data = r.json()

                messages.extend(data.get("value", []))

                endpoint = data.get("@odata.nextLink")
                params = None

        print(
            f"[OUTLOOK] {len(messages)} messages found since "
            f"{since.strftime('%Y-%m-%d %H:%M')} UTC"
        )

        results = []

        for message in messages:

            subject = message.get("subject", "")
            body = message.get("bodyPreview", "")

            event = classify_email(subject, body)

            if not event:
                continue

            from_address = message.get("from", {}).get("emailAddress", {})

            # "Name <address>" - same shape as Gmail's raw From header -
            # so extract_email_company can read the display name too
            # (needed for ATS platforms like SmartRecruiters where the
            # real employer is in the display name, not the domain).
            sender_name = from_address.get("name", "")
            sender_email = from_address.get("address", "")

            sender = (
                f"{sender_name} <{sender_email}>"
                if sender_name
                else sender_email
            )

            if is_generic_job_alert(subject, body, sender):
                continue

            body_field = message.get("body", {}) or {}
            body_content = body_field.get("content", "") or ""

            full_body = (
                strip_html(body_content)
                if body_field.get("contentType") == "html"
                else clean_body_text(body_content)
            )[:20000]

            item = {
                "id": message.get("id"),
                "subject": subject,
                "from": sender,
                "received": message.get("receivedDateTime"),
                "bodyPreview": body,
                "body": full_body,
                "webLink": message.get("webLink"),
                "_type": event,
                "_account": "outlook",
            }

            results.append(item)

            print(
                f"[OUTLOOK] MATCH [{event}] "
                f"{subject[:80]}"
            )

        print(
            f"[OUTLOOK] "
            f"{len(results)} relevant application emails"
        )

        return results, None

    except requests.Timeout:
        print("[OUTLOOK] TIMEOUT")
        return [], "Request timed out."

    except Exception as e:
        print(f"[OUTLOOK] ERROR {e}")
        return [], str(e)


# ============================================================
# COMPANY EXTRACTION
# ============================================================

def clean_company(value):
    if not value:
        return ""

    value = value.strip()

    value = re.sub(
        r"^(no-reply|noreply|reply|notifications?)@",
        "",
        value,
        flags=re.I
    )

    value = value.split("@")[-1]

    value = value.split(".")[0]

    return normalize(value)


# ============================================================
# COMPANY EXTRACTION - ATS / PLATFORM HANDLING
# ============================================================
#
# A large share of application emails don't come from the hiring
# company's own domain - they come from a shared ATS/recruiting
# platform (SmartRecruiters, Workday, Greenhouse, Lever, ...) that
# sends on behalf of hundreds of different employers. Using that
# platform's domain as "the company" mislabels every job under the
# same wrong name (e.g. 32 different employers all showing up as
# "Myworkday"). Each entry below and its evidence came from auditing
# this account's actual synced data.

ATS_DOMAINS = {
    "smartrecruiters",
    "greenhouse", "greenhouse-mail",
    "lever",
    "icims",
    "successfactors",
    "ashbyhq",
    "gr8people",
    "hackajob",
    "recruitee-email", "recruitee",
    "turbohire",
    "taleo",
    "bamboohr",
    "jobvite",
    "jazzhr",
    "breezy",
    "workable",
    "teamtailor",
    "avature",
    "phenom",
    "eightfold",
    "jobscore",
    "dover",
    "naukri",
    "jobringer",
    "hcm-talentkonnect",
}

# Workday is its own case: the ATS domain is myworkday.com, but the
# LOCAL PART of the sender address is the company's own slug (e.g.
# "geaerospace@myworkday.com" -> GE Aerospace, "pwc@myworkday.com" ->
# PwC) - the opposite of the usual domain-is-the-signal case.
WORKDAY_DOMAIN_SUFFIXES = ("myworkday.com", "workday.com")

# ATS platforms where the sender's DISPLAY NAME ("SWIGGY
# <notification@smartrecruiters.com>") reliably carries the real
# employer name, confirmed against this account's actual data.
# Other ATS platforms send from a recruiter's personal name instead
# (e.g. Hackajob), where trusting the display name would be wrong -
# those fall through to subject-text extraction instead.
DISPLAY_NAME_TRUSTED_DOMAINS = {"smartrecruiters", "naukri"}

# Personal webmail - never a "company", but does show up as the
# sender when the user CCs/forwards themselves or a recruiter emails
# from a personal account.
PERSONAL_EMAIL_DOMAINS = {
    "gmail.com", "outlook.com", "hotmail.com", "yahoo.com",
    "live.com", "icloud.com", "protonmail.com", "aol.com",
}

# Suffixes to strip off an otherwise-usable display name, e.g.
# "Oracle Talent Acquisition" -> "Oracle", "Revolut Recruitment" ->
# "Revolut".
DISPLAY_NAME_SUFFIXES = [
    "talent acquisition", "recruitment", "recruiting", "careers",
    "hiring team", "talent team", "hr team", "hr",
]

COMPANY_TEXT_PATTERNS = [
    r"has received your application",
    r"has your application",
    r"thank(?:s| you) for (?:your )?applying to\s+",
    r"applying to\s+",
    r"thank(?:s| you) for your (?:interest|application) (?:in|at|to)\s+",
    r"application at\s+",
    r"application (?:for|to)\s+.+?\s+at\s+",
    r"applying (?:for|to)\s+.+?\s+at\s+",
    r"interview (?:update|invitation) with\s+",
    r"^(.+?):\s*application",
]


def sender_domain(sender):
    if "@" not in sender:
        return ""

    domain = sender.split("@")[-1].split(">")[0].strip().lower()

    return domain


def sender_local_part(sender):
    if "@" not in sender:
        return ""

    local = sender.split("@")[0]

    if "<" in local:
        local = local.rsplit("<", 1)[-1]

    return re.sub(
        r"^(hr|careers|jobs|recruiting|noreply|no-reply)[-._]*",
        "",
        local.strip(),
        flags=re.I,
    )


def sender_display_name(sender):
    if "<" not in sender:
        return ""

    return sender.split("<")[0].strip().strip('"')


def clean_display_name(name):
    text = name
    lowered = text.lower()

    for suffix in DISPLAY_NAME_SUFFIXES:
        idx = lowered.find(suffix)

        if idx > 0:
            text = text[:idx].strip(" -–|,")
            lowered = text.lower()

    return text.strip()


def extract_company_from_text(text):
    for anchor in COMPANY_TEXT_PATTERNS:

        # Case-insensitive only for the anchor phrase - real subjects
        # often capitalize it as the first word ("Interview update
        # with X!", "Thank You for Applying to X") - the captured
        # name itself still has to start uppercase, a reasonable
        # signal that it's a proper noun.
        match = re.search(
            r"(?i:" + anchor + r")"
            r"([A-Z][\w&.,'’ ()-]{1,50}?)(?:[!.\n]|\s+is\s|\s*$)",
            text,
        )

        if match:
            candidate = normalize(match.group(1))

            if candidate:
                return candidate

    return ""


def extract_email_company(email):
    sender = email.get("from") or ""
    subject = email.get("subject", "")
    body = email.get("bodyPreview", "")

    domain = sender_domain(sender)
    domain_root = domain.split(".")[-2] if domain.count(".") >= 1 else domain

    # Workday: company lives in the local part, not the domain.
    if any(domain.endswith(suffix) for suffix in WORKDAY_DOMAIN_SUFFIXES):
        local = sender_local_part(sender)

        if local:
            return normalize(local)

    is_ats = domain_root in ATS_DOMAINS
    is_personal = domain in PERSONAL_EMAIL_DOMAINS

    if not is_ats and not is_personal and domain_root:
        return normalize(domain_root)

    if is_ats and domain_root in DISPLAY_NAME_TRUSTED_DOMAINS:
        display = clean_display_name(sender_display_name(sender))

        if display and normalize(display) not in ATS_DOMAINS:
            return normalize(display)

    for text in (subject, body):
        candidate = extract_company_from_text(text)

        if candidate and candidate not in ATS_DOMAINS:
            return candidate

    # ATS/personal sender with nothing extractable from the text -
    # "Unknown Company" is an honest fallback; the ATS platform's own
    # name would be a confident-looking wrong answer.
    return ""


# ============================================================
# JOB MATCHING
# ============================================================

def company_matches(job_company, email):
    job = normalize(job_company)

    if not job:
        return False

    email_company = extract_email_company(email)

    if not email_company:
        return False

    if job == email_company:
        return True

    if job in email_company:
        return True

    if email_company in job:
        return True

    # Handle common company-name variants
    job_words = set(job.split())
    email_words = set(email_company.split())

    common = job_words.intersection(email_words)

    return len(common) >= 1


def role_matches(job_role, email):
    role = normalize(job_role)

    if not role:
        return True

    text = normalize(
        f"{email.get('subject', '')} "
        f"{email.get('bodyPreview', '')}"
    )

    role_words = [
        word
        for word in role.split()
        if len(word) >= 3
    ]

    if not role_words:
        return True

    matches = sum(
        1 for word in role_words
        if word in text
    )

    # Role matching is flexible because companies
    # frequently abbreviate job titles.
    return matches >= min(2, len(role_words))


def find_best_job(email, jobs):
    """Given an email, find the existing job it most likely belongs to.
    Requires a company match (a real signal) before a job is even
    considered, exactly like the original per-job email matching did."""

    candidates = []

    for job in jobs:

        if not company_matches(job.company, email):
            continue

        score = 50

        if role_matches(job.role, email):
            score += 40

        event = email.get("_type")

        if event in ("application_received", "assessment", "interview", "rejected"):
            score += 25

        elif event == "offer":
            score += 30

        candidates.append((score, job))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)

    return candidates[0][1]


# ============================================================
# DB SYNC
# ============================================================

def apply_emails_to_db(db, all_emails):
    """Merge classified emails into the Job/JobEvent tables. Emails that
    match an existing job (by company, optionally role) become a new
    timeline event on that job. Emails that don't match anything become
    a brand-new job - this is what makes the dashboard auto-populate
    from email instead of requiring jobs to be entered by hand.
    """

    existing_email_ids = {
        row[0]
        for row in db.query(JobEvent.email_id).filter(
            JobEvent.email_id.isnot(None)
        ).all()
    }

    working_jobs = db.query(Job).all()

    jobs_created = 0
    events_added = 0
    jobs_updated = set()
    rejected_count = 0
    needs_review_count = 0

    # Oldest first, so a job's timeline and status build up in the
    # correct chronological order.
    ordered_emails = sorted(
        all_emails,
        key=lambda e: parse_received(e.get("received")),
    )

    for email in ordered_emails:

        email_id = email.get("id")

        if email_id and email_id in existing_email_ids:
            continue

        received_date = parse_received(email.get("received"))
        event_type = email.get("_type")

        job = find_best_job(email, working_jobs)

        created_new = False

        if job is None:
            company = extract_email_company(email)
            role = guess_role(
                email.get("subject", ""),
                email.get("bodyPreview", "")
            )

            company_display = company.title() if company else "Unknown Company"

            status = event_type if company else "needs_review"

            if not company:
                needs_review_count += 1

            job = Job(
                company=company_display,
                role=role,
                job_id="",
                status=status,
                source_account=email.get("_account", ""),
                applied_date=received_date,
                last_activity=received_date,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            db.add(job)
            db.flush()  # assign job.id so the JobEvent FK is valid

            working_jobs.append(job)

            jobs_created += 1
            created_new = True

        event = JobEvent(
            job_id=job.id,
            event_type=event_type,
            subject=email.get("subject", ""),
            sender=email.get("from", ""),
            account=email.get("_account", ""),
            email_id=email_id,
            web_link=email.get("webLink", ""),
            body=email.get("body", ""),
            received_date=received_date,
            created_at=datetime.utcnow(),
        )

        db.add(event)
        job.events.append(event)

        if email_id:
            existing_email_ids.add(email_id)

        events_added += 1

        if event_type == "rejected":
            rejected_count += 1

        if not created_new:
            jobs_updated.add(job.id)

        if received_date > (job.last_activity or received_date):
            job.last_activity = received_date

        if STATUS_PRIORITY.get(event_type, 0) >= STATUS_PRIORITY.get(job.status, 0):
            job.status = event_type

        job.updated_at = datetime.utcnow()

    db.commit()

    return {
        "jobs_created": jobs_created,
        "jobs_updated": len(jobs_updated),
        "events_added": events_added,
        "rejected_count": rejected_count,
        "needs_review_count": needs_review_count,
    }


# ============================================================
# INCREMENTAL SYNC CUTOFF
# ============================================================
#
# Every sync used to re-scan the full SYNC_WINDOW_DAYS window from
# scratch - existing_email_ids in apply_emails_to_db() stopped it from
# creating duplicates, but every message still got re-fetched (full
# body and all) every single time, which is most of why a sync took
# so long even when nothing new had arrived. Instead, each account
# picks up from where its last sync left off.

# A small overlap past the newest event we already have, so a clock
# skew or same-second ordering quirk on the mail server can't cause a
# message right at the boundary to be silently skipped.
SYNC_OVERLAP = timedelta(hours=6)


def account_sync_cutoff(db, account):
    latest = (
        db.query(func.max(JobEvent.received_date))
        .filter(JobEvent.account == account)
        .scalar()
    )

    if latest:
        return latest - SYNC_OVERLAP

    # No prior sync for this account - fall back to the full window.
    return datetime.utcnow() - timedelta(days=SYNC_WINDOW_DAYS)


# ============================================================
# FULL 5 ACCOUNT SYNC
# ============================================================

sync_lock = threading.Lock()


@app.post("/sync")
def full_sync():
    """Manual trigger (the dashboard's "Sync Emails" button) - a
    fallback for whenever the automatic background sync hasn't run
    recently enough. Runs the exact same sync as the automatic one;
    the two share sync_lock so they can never run concurrently and
    stomp on each other."""

    if not sync_lock.acquire(blocking=False):
        return {
            "success": False,
            "message": (
                "A sync is already running in the background - "
                "give it a moment and refresh."
            ),
        }

    try:
        return perform_sync(trigger="manual")
    finally:
        sync_lock.release()


def perform_sync(trigger="manual"):

    print("")
    print("=" * 60)
    print(f"FULL JOB APPLICATION SYNC STARTED ({trigger})")
    print("Gmail x4 + Outlook x1")
    print("=" * 60)

    all_emails = []

    source_counts = {}

    errors = []

    cutoff_db = SessionLocal()

    try:
        gmail_cutoffs = {
            f"gmail_{index}": account_sync_cutoff(cutoff_db, f"gmail_{index}")
            for index in range(1, len(GMAIL_FILES) + 1)
        }
        outlook_cutoff = account_sync_cutoff(cutoff_db, "outlook")
    finally:
        cutoff_db.close()

    # -------------------------
    # GMAIL 1-4
    # -------------------------

    for index, path in enumerate(
        GMAIL_FILES,
        start=1
    ):

        account = f"gmail_{index}"

        # 1000 is the per-request cap - a busy account can receive
        # more than that, but since this is now incremental (only
        # since the last sync's cutoff, not the full 30-day window
        # every time) hitting the cap on a routine sync would mean
        # an unusually large burst of mail since last time.
        emails, error = scan_gmail(
            account,
            path,
            max_messages=1000,
            since=gmail_cutoffs[account],
        )

        source_counts[account] = len(emails)

        all_emails.extend(emails)

        if error:
            errors.append({"account": account, "error": error})
            ACCOUNT_STATE[account] = {
                "status": "error",
                "message": error,
                "checked_at": now_iso(),
            }
        else:
            ACCOUNT_STATE[account] = {
                "status": "connected",
                "message": None,
                "checked_at": now_iso(),
            }

    # -------------------------
    # OUTLOOK
    # -------------------------

    outlook_emails, outlook_error = scan_outlook(
        max_messages=1000,
        since=outlook_cutoff,
    )

    source_counts["outlook"] = len(
        outlook_emails
    )

    all_emails.extend(
        outlook_emails
    )

    if outlook_error:
        errors.append({"account": "outlook", "error": outlook_error})
        ACCOUNT_STATE["outlook"] = {
            "status": "error",
            "message": outlook_error,
            "checked_at": now_iso(),
        }
    else:
        ACCOUNT_STATE["outlook"] = {
            "status": "connected",
            "message": None,
            "checked_at": now_iso(),
        }

    # -------------------------
    # MERGE INTO DATABASE
    # -------------------------

    db = SessionLocal()

    try:
        stats = apply_emails_to_db(db, all_emails)
        total_jobs = db.query(Job).count()
    finally:
        db.close()

    print("")
    print("=" * 60)
    print("SYNC FINISHED")
    print(f"Relevant emails: {len(all_emails)}")
    print(f"Jobs created: {stats['jobs_created']}")
    print(f"Jobs updated: {stats['jobs_updated']}")
    print(f"Rejected: {stats['rejected_count']}")
    print("=" * 60)

    # ------------------------------------------------------------
    # LIVE JOBS
    # Runs inside the existing 5-minute sync loop.
    # No second background thread is created.
    # ------------------------------------------------------------
    live_jobs_discovered = 0
    live_jobs_error = None

    try:
        live_jobs_db = SessionLocal()
        try:
            live_jobs_discovered = discover_all_companies(live_jobs_db)
        finally:
            live_jobs_db.close()
    except Exception as e:
        live_jobs_error = str(e)
        print(f"[LIVE JOBS] discovery failed: {e}")

    print(
        f"[LIVE JOBS] discovered={live_jobs_discovered}"
    )

    return {
        "success": True,
        "message": "Full 5-account synchronization completed",
        "accounts": {
            "gmail": 4,
            "outlook": 1,
            "total": 5,
        },
        "relevant_emails": len(all_emails),
        "source_counts": source_counts,
        "total_jobs": total_jobs,
        "jobs_created": stats["jobs_created"],
        "jobs_updated": stats["jobs_updated"],
        "matched": stats["jobs_updated"],
        "new_events": stats["events_added"],
        "rejected_count": stats["rejected_count"],
        "needs_review_count": stats["needs_review_count"],
        "errors": errors,
    }


# ============================================================
# AUTOMATIC BACKGROUND SYNC
# ============================================================
#
# The dashboard's "Sync Emails" button is a fallback for whenever
# this hasn't run recently enough on its own - normally nothing needs
# to be clicked. Runs every AUTO_SYNC_INTERVAL_SECONDS on a daemon
# thread; incremental syncing (account_sync_cutoff) is what makes
# running this often cheap instead of re-scanning everything each
# time.

AUTO_SYNC_INTERVAL_SECONDS = 5 * 60

AUTO_SYNC_STATE = {
    "last_run_at": None,
    "last_result": None,
    "next_run_at": None,
    "running": False,
}


def _background_sync_loop():
    # Give the app a moment to finish starting up before the first
    # sync, then run one right away rather than waiting a full
    # interval - "always live" means catching up as soon as possible,
    # not just on some future schedule.
    time.sleep(15)

    while True:
        if sync_lock.acquire(blocking=False):

            AUTO_SYNC_STATE["running"] = True

            try:
                result = perform_sync(trigger="auto")

                AUTO_SYNC_STATE["last_result"] = {
                    "success": result.get("success"),
                    "relevant_emails": result.get("relevant_emails"),
                    "jobs_created": result.get("jobs_created"),
                    "jobs_updated": result.get("jobs_updated"),
                    "errors": result.get("errors"),
                }

            except Exception as e:
                print(f"[AUTO-SYNC] failed: {e}")
                print(traceback.format_exc())

                AUTO_SYNC_STATE["last_result"] = {
                    "success": False,
                    "error": str(e),
                }

            finally:
                sync_lock.release()

                AUTO_SYNC_STATE["running"] = False
                AUTO_SYNC_STATE["last_run_at"] = now_iso()

        else:
            # A manual sync is already running - skip this tick
            # rather than queue up behind it.
            print("[AUTO-SYNC] skipped - a sync is already in progress")

        next_run = datetime.now(timezone.utc) + timedelta(
            seconds=AUTO_SYNC_INTERVAL_SECONDS
        )
        AUTO_SYNC_STATE["next_run_at"] = next_run.isoformat()

        time.sleep(AUTO_SYNC_INTERVAL_SECONDS)


# ============================================================
# DASHBOARD
# ============================================================

def empty_status_counts():
    return {status: 0 for status in STATUS_PRIORITY.keys()}


@app.get("/dashboard")
def dashboard():

    db = SessionLocal()

    try:
        jobs = db.query(Job).order_by(Job.last_activity.desc()).all()

        statuses = empty_status_counts()

        for job in jobs:
            status = job.status if job.status in statuses else "needs_review"
            statuses[status] += 1

        return {
            "success": True,
            "summary": {
                "total": len(jobs),
                **statuses,
            },
            "jobs": [job.to_dict() for job in jobs],
        }
    finally:
        db.close()


# ============================================================
# JOBS
# ============================================================

@app.get("/jobs")
def get_jobs():

    db = SessionLocal()

    try:
        jobs = (
            db.query(Job)
            .order_by(Job.last_activity.desc())
            .all()
        )

        return {
            "success": True,
            "total": len(jobs),
            "jobs": [job.to_dict() for job in jobs],
        }
    finally:
        db.close()


@app.get("/jobs/{job_id}")
def get_job_detail(job_id: int):

    db = SessionLocal()

    try:
        job = db.query(Job).filter(Job.id == job_id).first()

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return {
            "success": True,
            "job": job.to_dict(include_events=True),
        }
    finally:
        db.close()


@app.post("/jobs")
def create_job(job: JobCreate):

    db = SessionLocal()

    try:
        try:
            applied_date = datetime.fromisoformat(
                job.applied_date.replace("Z", "+00:00")
            ).replace(tzinfo=None)
        except Exception:
            applied_date = datetime.utcnow()

        new_job = Job(
            company=job.company,
            role=job.role,
            job_id=job.job_id,
            status="applied",
            source_account="manual",
            applied_date=applied_date,
            last_activity=applied_date,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(new_job)
        db.commit()
        db.refresh(new_job)

        return {
            "success": True,
            "job": new_job.to_dict(),
        }
    finally:
        db.close()


# ============================================================
# SUMMARY
# ============================================================

@app.get("/jobs/summary")
def jobs_summary():

    db = SessionLocal()

    try:
        jobs = db.query(Job).all()

        statuses = empty_status_counts()

        for job in jobs:
            status = job.status if job.status in statuses else "needs_review"
            statuses[status] += 1

        return {
            "success": True,
            "total": len(jobs),
            "statuses": statuses,
        }
    finally:
        db.close()


# ============================================================
# HEALTH
# ============================================================



@app.get("/health")
def health():

    return {
        "status": "healthy"
    }


# ============================================================
# MICROSOFT (OUTLOOK) LOGIN
#
# Device-code auth (see outlook_sync.py) requires "Allow public
# client flows" on the Azure app registration. This is the
# alternative, browser-based authorization-code flow: it needs the
# app registration to have OUTLOOK_REDIRECT_URI (from .env) registered
# as a Web platform redirect URI instead. Whichever the Azure app is
# actually configured for, this is what /sync/status + the frontend
# Settings page rely on to (re)connect the Outlook account.
# ============================================================

@app.get("/auth/microsoft/login")
def microsoft_login():
    return RedirectResponse(get_login_url())


@app.get("/auth/microsoft/callback")
def microsoft_callback(request: Request):

    code = request.query_params.get("code")

    if not code:
        raise HTTPException(status_code=400, detail="Authorization code missing")

    try:
        result = get_token(code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if "access_token" not in result:
        raise HTTPException(
            status_code=400,
            detail=result.get("error_description") or result.get("error") or "Login failed",
        )

    token = result["access_token"]

    response = requests.get(
        f"{GRAPH_URL}/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    user = response.json()

    account = user.get("mail") or user.get("userPrincipalName")
    name = user.get("displayName")

    TOKEN_DIR.mkdir(exist_ok=True)

    with open(OUTLOOK_TOKEN, "w", encoding="utf-8") as f:
        json.dump({"account": account, "name": name, "token": result}, f, indent=2)

    ACCOUNT_STATE["outlook"] = {
        "status": "connected",
        "message": None,
        "checked_at": now_iso(),
    }

    return {
        "success": True,
        "message": "Microsoft Outlook connected successfully",
        "account": account,
        "name": name,
    }


# ============================================================
# DIAGNOSTICS
# ============================================================

def account_status_from_files(token_available, exists):
    if not exists or not token_available:
        return "auth_required"

    return "connected"


@app.get("/sync/status")
def sync_status():

    files = {}

    for path, account in zip(GMAIL_FILES, ["gmail_1", "gmail_2", "gmail_3", "gmail_4"]):

        token_available = get_gmail_token(path) is not None

        state = ACCOUNT_STATE.get(account)

        status = (
            state["status"]
            if state
            else account_status_from_files(token_available, path.exists())
        )

        files[path.name] = {
            "exists": path.exists(),
            "size": (
                path.stat().st_size
                if path.exists()
                else 0
            ),
            "token_available": token_available,
            "status": status,
            "message": state["message"] if state else None,
        }

    outlook_token_available = get_outlook_token() is not None

    outlook_state = ACCOUNT_STATE.get("outlook")

    outlook_status = (
        outlook_state["status"]
        if outlook_state
        else account_status_from_files(outlook_token_available, OUTLOOK_TOKEN.exists())
    )

    files["outlook_1.json"] = {
        "exists": OUTLOOK_TOKEN.exists(),
        "size": (
            OUTLOOK_TOKEN.stat().st_size
            if OUTLOOK_TOKEN.exists()
            else 0
        ),
        "token_available": outlook_token_available,
        "status": outlook_status,
        "message": outlook_state["message"] if outlook_state else None,
    }

    return {
        "success": True,
        "token_directory": str(TOKEN_DIR),
        "accounts": files,
        "auto_sync": {
            "interval_minutes": AUTO_SYNC_INTERVAL_SECONDS // 60,
            **AUTO_SYNC_STATE,
        },
    }


# ============================================================
# FRONTEND (built React app) - only present in the deployed
# container, where the Dockerfile builds frontend/dist and this
# process serves it alongside the API on the same port. Registered
# last so every API route above still takes priority; not mounted at
# all in local dev (no dist/ there), where the Vite dev server on
# :5173 serves the frontend instead.
# ============================================================

FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Any real built asset (JS/CSS bundle, favicon, ...) is served
        # directly; everything else is a React Router client-side
        # route (e.g. /applications) - not a real file - so fall back
        # to index.html and let the SPA router handle it.
        candidate = FRONTEND_DIST / full_path

        if full_path and candidate.is_file():
            return FileResponse(candidate)

        return FileResponse(FRONTEND_DIST / "index.html")
