import os
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

load_dotenv()


CLIENT_ID = os.getenv("OUTLOOK_CLIENT_ID")
CLIENT_SECRET = os.getenv("OUTLOOK_CLIENT_SECRET")
TENANT_ID = os.getenv("OUTLOOK_TENANT_ID", "common")
REDIRECT_URI = os.getenv(
    "OUTLOOK_REDIRECT_URI",
    "http://localhost:8765"
)

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
AUTHORIZE_URL = f"{AUTHORITY}/oauth2/v2.0/authorize"
TOKEN_URL = f"{AUTHORITY}/oauth2/v2.0/token"

SCOPES = [
    "openid",
    "profile",
    "offline_access",
    "User.Read",
    "Mail.Read",
]


def get_login_url():
    if not CLIENT_ID:
        raise RuntimeError("OUTLOOK_CLIENT_ID is missing")

    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "response_mode": "query",
        "scope": " ".join(SCOPES),
        "prompt": "select_account",
    }

    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def get_token(code):
    if not CLIENT_ID:
        raise RuntimeError("OUTLOOK_CLIENT_ID is missing")

    if not CLIENT_SECRET:
        raise RuntimeError("OUTLOOK_CLIENT_SECRET is missing")

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
        "scope": " ".join(SCOPES),
    }

    response = requests.post(
        TOKEN_URL,
        data=data,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def refresh_access_token(refresh_token):
    """Exchange a stored refresh_token for a new access token. Access
    tokens are short-lived (~1hr); without this, any sync started a
    while after login - or one that just runs long, like scanning a
    high-volume mailbox - starts failing every request with 401."""

    if not CLIENT_ID:
        raise RuntimeError("OUTLOOK_CLIENT_ID is missing")

    if not CLIENT_SECRET:
        raise RuntimeError("OUTLOOK_CLIENT_SECRET is missing")

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "scope": " ".join(SCOPES),
    }

    response = requests.post(
        TOKEN_URL,
        data=data,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()