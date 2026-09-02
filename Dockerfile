# ---- frontend build ----
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- backend runtime (serves the API + the built frontend) ----
FROM python:3.13-slim
WORKDIR /app/backend

COPY backend/requirements.txt backend/requirements-browser.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Optional: the live_jobs `browser` source (headless Chromium for
# JS-only careers sites). Adds ~400 MB. Build with
# `--build-arg LIVE_JOBS_BROWSER=1` to enable; the adapter no-ops if the
# browser isn't present.
ARG LIVE_JOBS_BROWSER=0
RUN if [ "$LIVE_JOBS_BROWSER" = "1" ]; then \
        pip install --no-cache-dir -r requirements-browser.txt && \
        playwright install --with-deps chromium ; \
    fi

COPY backend/ ./
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

# DATA_DIR is where db.py/main.py put job_tracker.sqlite3 and the
# OAuth token files - mount a volume here so they survive container
# restarts/redeploys instead of living in the image's writable layer.
ENV DATA_DIR=/data
VOLUME /data

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
