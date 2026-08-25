# Job Application Tracker

Tracks job applications automatically by scanning Gmail and Outlook
inboxes for application-related emails (confirmations, assessments,
interviews, offers, rejections), matching them to a job by
company/role, and rolling each job up to its most advanced status.

## Structure

- `backend/` — FastAPI + SQLAlchemy (SQLite) API. Syncs Gmail (OAuth,
  `google-api-python-client`) and Outlook (Microsoft Graph OAuth)
  accounts, classifies emails by keyword/pattern matching, and
  exposes `/jobs`, `/dashboard`, `/sync`, and related endpoints.
- `frontend/` — React + TypeScript + Vite dashboard (Tailwind CSS)
  for browsing applications, filtering by status/source, and
  triggering a manual sync.

## Running locally

**Backend**

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate  # .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Requires a `.env` file in `backend/` with Outlook OAuth credentials
(`OUTLOOK_CLIENT_ID`, `OUTLOOK_CLIENT_SECRET`, `OUTLOOK_TENANT_ID`,
`OUTLOOK_REDIRECT_URI`) and, for Gmail, per-account token files under
`backend/tokens/`.

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Defaults to talking to the backend on the same host, port 8000
(override with `VITE_API_URL`).

## Notes

- `backend/tokens/` (OAuth tokens) and `backend/job_tracker.sqlite3`
  (synced email/job data) are gitignored — both are personal,
  account-specific data, not source.
- The dev server binds `0.0.0.0` and the backend's CORS config
  accepts localhost, LAN, and Tailscale (`100.x.x.x` / `*.ts.net`)
  origins, so the dashboard is reachable from other devices on the
  same tailnet without extra config.
