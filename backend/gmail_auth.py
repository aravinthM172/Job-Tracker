"""One-off (re)authorisation for the 4 Gmail accounts.

main.py can *refresh* a Gmail access token on its own, but only while the
stored refresh_token is still valid. When Google invalidates the
refresh_token itself - the OAuth consent screen is in "Testing" mode
(refresh tokens then expire after 7 days), access was revoked, or the
account password changed - every sync starts coming back as
"Token expired or invalid (401). Re-authenticate." and there is no way
back in from the running app (unlike Outlook, there is no
/auth/google/* route).

Run this script to redo the browser consent for the broken accounts and
rewrite their token files:

    # re-auth every account whose token currently fails to refresh
    python gmail_auth.py

    # or target specific ones
    python gmail_auth.py 2 4

The OAuth client id/secret are read from (in order):
  1. $GOOGLE_CREDENTIALS_FILE, or backend/credentials.json  (a normal
     "Desktop app" client_secret json downloaded from Google Cloud)
  2. failing that, whatever is already baked into an existing
     tokens/gmail_*.json (they are full Credentials.to_json() blobs, so
     client_id + client_secret are in there).

Needs a browser on this machine - it spins up a localhost redirect
listener, same as the original setup did.
"""

import json
import os
import sys
from pathlib import Path

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials as GoogleCredentials
from google_auth_oauthlib.flow import InstalledAppFlow

BASE_DIR = Path(__file__).resolve().parent
TOKEN_DIR = BASE_DIR / "tokens"

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

ACCOUNTS = [1, 2, 3, 4]


def token_path(n: int) -> Path:
    return TOKEN_DIR / f"gmail_{n}.json"


def load_client_config() -> dict:
    """Return an InstalledAppFlow-style {"installed": {...}} client config."""

    explicit = os.getenv("GOOGLE_CREDENTIALS_FILE")
    candidates = [Path(explicit)] if explicit else []
    candidates.append(BASE_DIR / "credentials.json")

    for path in candidates:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            # Google hands these out as {"installed": {...}} or
            # {"web": {...}}; InstalledAppFlow wants "installed".
            if "installed" in data:
                return data
            if "web" in data:
                return {"installed": data["web"]}
            return {"installed": data}

    # Fall back to the client baked into an existing token file.
    for n in ACCOUNTS:
        path = token_path(n)
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("client_id") and data.get("client_secret"):
            print(f"[gmail-auth] using OAuth client from {path.name}")
            return {
                "installed": {
                    "client_id": data["client_id"],
                    "client_secret": data["client_secret"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": data.get(
                        "token_uri", "https://oauth2.googleapis.com/token"
                    ),
                }
            }

    sys.exit(
        "No OAuth client found. Put a Desktop-app client_secret json at "
        "backend/credentials.json (or set $GOOGLE_CREDENTIALS_FILE)."
    )


def refresh_ok(path: Path) -> bool:
    """True if this token file can still mint a fresh access token."""

    if not path.exists():
        return False

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        creds = GoogleCredentials.from_authorized_user_info(
            data, data.get("scopes")
        )
        if creds.valid:
            return True
        if creds.expired and creds.refresh_token:
            creds.refresh(GoogleAuthRequest())
            return True
    except Exception:
        return False

    return False


def account_email(creds: GoogleCredentials) -> str:
    """Best-effort: ask Gmail whose mailbox this token is for, so the
    rewritten file keeps a meaningful "account" field."""

    import requests

    try:
        r = requests.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/profile",
            headers={"Authorization": f"Bearer {creds.token}"},
            timeout=15,
        )
        if r.status_code == 200:
            return r.json().get("emailAddress", "")
    except Exception:
        pass

    return ""


def reauth(n: int, client_config: dict) -> None:
    path = token_path(n)
    print(f"\n=== gmail_{n} ===")
    print("A browser window will open - sign in with the correct Google account.")

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    # port=0 -> random free localhost port; access_type=offline + prompt=
    # consent forces Google to return a fresh refresh_token every time.
    creds = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",
    )

    blob = json.loads(creds.to_json())
    blob["account"] = account_email(creds)

    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(blob, indent=2), encoding="utf-8")

    print(f"[gmail-auth] wrote {path.name}  (account: {blob['account'] or 'unknown'})")


def main() -> None:
    args = [int(a) for a in sys.argv[1:] if a.isdigit()]
    targets = args or ACCOUNTS

    client_config = load_client_config()

    to_fix = []
    for n in targets:
        if not args and refresh_ok(token_path(n)):
            print(f"[gmail-auth] gmail_{n}: still OK, skipping")
            continue
        to_fix.append(n)

    if not to_fix:
        print("[gmail-auth] nothing to do - all target accounts refresh fine.")
        return

    print(f"[gmail-auth] will re-authorise: {', '.join(f'gmail_{n}' for n in to_fix)}")

    for n in to_fix:
        reauth(n, client_config)

    print("\n[gmail-auth] done. Restart the backend (or wait for the next")
    print("auto-sync) and the accounts should come back as connected.")


if __name__ == "__main__":
    main()
