# Job Application Tracker

Two things in one app:

1. **Application tracker** — scans Gmail and Outlook inboxes for
   application-related email (confirmations, assessments, interviews,
   offers, rejections), matches each message to a job by company/role,
   and rolls every job up to its most advanced status.
2. **Live Jobs** — continuously discovers fresh openings straight from
   ~155 tracked companies' careers sites (Bengaluru + Hyderabad by
   default) and shows them on a live-updating page with status (new /
   live / reposted / closed), experience range, source, and post date.

A session login gates the app. The owner sees everything; **viewer**
accounts (created by the owner in Settings) can open only the Live Jobs
page — so the page can be shared without exposing synced email.

## Structure

- `backend/` — FastAPI + SQLAlchemy (SQLite) API.
  - Email sync: Gmail (`google-api-python-client` OAuth) and Outlook
    (Microsoft Graph OAuth); keyword/pattern classification; endpoints
    `/api/jobs`, `/api/dashboard`, `/api/sync`, …
  - `live_jobs/` — the Live Jobs subsystem (see below). Discovery runs
    inside the existing 5-minute auto-sync loop, no extra thread.
- `frontend/` — React 19 + TypeScript + Vite + Tailwind CSS 4 dashboard.
  Login page, role-aware nav (viewers get Live Jobs only), Applications
  view, Live Jobs view, manual sync, light/dark theme (toggle in the
  top bar, remembered in `localStorage`), a pipeline funnel on the
  dashboard, and a `Cmd/Ctrl+K` palette to jump to a page or company.
- `backend/auth.py` — session login: `users` + `auth_sessions` tables,
  scrypt password hashing, opaque httpOnly session cookies, per-IP
  login throttle. `main.py`'s middleware 403s a viewer on anything
  but `/api/live-jobs*`.

## Live Jobs

- **Allowlist** — `backend/live_jobs/companies.py` is the single source
  of truth. A posting is only discovered and only shown if its company
  matches a name there. `is_target_company()` tolerates ATS naming
  drift ("KPMG Global Services" ~ "KPMG").
- **Company → ATS map** — `backend/live_jobs/company_sources.py` maps
  each company to one or more `(source, token)` pairs.
- **Source adapters** — `backend/live_jobs/sources/`, one module per
  platform:
  - ATS APIs: Greenhouse, Lever, Ashby, Workday (CXS), Oracle Cloud
    Recruiting, SmartRecruiters, SuccessFactors, Keka, Darwinbox,
    Eightfold (PCS X), Phenom People, MyNextHire, Avature, Radancy /
    TalentBrew.
  - First-party feeds: Amazon.jobs, Meta, Google, Goldman Sachs
    (`higher.gs.com`), sitemap + JSON-LD.
  - `browser` — headless Chromium (Playwright) for careers sites that
    render jobs only in JS. Optional; no-ops if Chromium isn't in the
    image.
  - `adzuna` — the one aggregator back-fill; every hit is re-checked
    against the allowlist per job.
- **Cadence** — light feeds every cycle (~5 min); `HEAVY_SOURCES` every
  4th cycle; `GUARDED_SOURCES` (Google, Meta, `browser`) every 6th.
  `DATELESS_SOURCES` publish no post date, so the backend stamps a
  placeholder and the UI shows "found" (discovery time) instead of
  "posted".
- **Location filter** — `LIVE_JOBS_LOCATIONS` env var; the default
  covers **Bengaluru + Hyderabad** (with the spellings / state names
  each ATS uses). Set `india` for the whole country, empty to disable.
  The Live Jobs page has a multi-select location chip row (the tracked
  metros + Remote / Hybrid); pick any combination. A posting listed in
  more than one city matches any of them and is labelled e.g.
  "Hyderabad · also Bengaluru".
- **Window** — the page shows the last 48 hours; a not-seen sweep marks
  postings `CLOSED` once they drop off their feed.
- **Save / track** — ⭐ bookmarks a posting (per-browser, `localStorage`);
  "Track" creates a real application row (status `applied`) so it flows
  into the Applications view. The nav item shows an "N new" badge for
  postings first seen in the last hour.

## Running locally

**Backend**

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate            # .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
pip install -r requirements-dev.txt     # tests
pip install -r requirements-browser.txt # optional: `browser` source
#   then: playwright install --with-deps chromium
uvicorn main:app --host 0.0.0.0 --port 8000
```

Needs `backend/.env` with Outlook OAuth credentials
(`OUTLOOK_CLIENT_ID`, `OUTLOOK_CLIENT_SECRET`, `OUTLOOK_TENANT_ID`,
`OUTLOOK_REDIRECT_URI`) and, for Gmail, per-account token files under
`backend/tokens/`.

With no `OWNER_USERNAME` / `OWNER_PASSWORD` set, login is disabled and
the whole app is open — fine for localhost / a private tailnet.

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Talks to the backend on the same host, port 8000 (override with
`VITE_API_URL`).

**Tests**

```bash
cd backend && .venv/Scripts/python -m pytest
```

## Deployment (Docker)

Single multi-stage image: Vite build → Python runtime that serves the
API and the built `frontend/dist` from one process.

```bash
docker compose up -d --build
```

- `docker-compose.yml` builds with `LIVE_JOBS_BROWSER=1` (installs
  Playwright + Chromium, ~1 GB) and publishes port 80 → 8000.
- `DATA_DIR=/data` is a named volume — `job_tracker.sqlite3` (which
  also holds the `users` / `auth_sessions` tables) and the OAuth token
  files live there and survive redeploys.
- `backend/.env` is loaded via `env_file`. Required for a public
  deploy:
  - `OWNER_USERNAME` / `OWNER_PASSWORD` — your login. The owner row is
    re-seeded from these on every boot. (Legacy `BASIC_AUTH_USER` /
    `BASIC_AUTH_PASS` still work as a fallback.)
  - `COOKIE_SECURE` — `1` forces the session cookie `Secure` (set it
    once TLS terminates in front); `0` disables; unset = auto from the
    request scheme.
- Viewer accounts to share Live Jobs are added by the owner under
  **Settings → People with access**. For fixed demo logins, set
  `DEMO_USERS="demo:demopass123,guest:guestpass456"` (comma-separated
  `name:password`, password 8+ chars) — these are seeded as viewers on
  every boot and removed when dropped from the var.

Redeploy: `git pull --ff-only && docker compose up -d --build`.

> **Serve this over HTTPS.** `docker-compose.yml` publishes plain HTTP
> on port 80; put Caddy or a Cloudflare Tunnel in front so the login
> and synced email aren't in cleartext. See the security review.

## Notes

- `backend/tokens/` and `backend/job_tracker.sqlite3` are gitignored —
  personal, account-specific data, not source.
- The dev server binds `0.0.0.0`; backend CORS accepts localhost, LAN,
  and Tailscale (`100.x.x.x` / `*.ts.net`) origins.
