import logging
import threading
import time

from db import SessionLocal

from .discovery import discover_all_companies
from .service import close_old_jobs

logger = logging.getLogger(__name__)

LIVE_JOBS_SYNC_INTERVAL_SECONDS = 5 * 60

_stop_event = threading.Event()
_thread = None


def run_live_jobs_sync():
    db = SessionLocal()

    try:
        discovered = discover_all_companies(db)
        closed = close_old_jobs(db)

        logger.info(
            "[LIVE JOBS] sync complete | discovered=%s | closed=%s",
            discovered,
            closed,
        )

    except Exception:
        logger.exception("[LIVE JOBS] sync failed")

    finally:
        db.close()


def _loop():
    logger.info(
        "[LIVE JOBS] scanner started | interval=%ss",
        LIVE_JOBS_SYNC_INTERVAL_SECONDS,
    )

    time.sleep(15)

    while not _stop_event.is_set():
        run_live_jobs_sync()
        _stop_event.wait(LIVE_JOBS_SYNC_INTERVAL_SECONDS)


def start_live_jobs_scanner():
    global _thread

    if _thread and _thread.is_alive():
        return

    _stop_event.clear()

    _thread = threading.Thread(
        target=_loop,
        name="live-jobs-scanner",
        daemon=True,
    )

    _thread.start()


def stop_live_jobs_scanner():
    _stop_event.set()
