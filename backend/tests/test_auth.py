"""Auth + role-gate tests.

The env's Starlette TestClient needs an http client that isn't installed,
so the integration checks run against a real uvicorn subprocess hit with
``requests`` (a runtime dependency). The crypto / session helpers are
unit-tested directly.
"""

import os
import socket
import subprocess
import sys
import tempfile
import time

import pytest
import requests

import auth

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OWNER = ("owner", "test-owner-pw-123")


# --------------------------------------------------------------------------
# unit: password hashing + sessions + throttle
# --------------------------------------------------------------------------

def test_password_hash_roundtrip():
    h = auth.hash_password("correct horse battery")
    assert h.startswith("scrypt$")
    assert auth.verify_password("correct horse battery", h)
    assert not auth.verify_password("Correct horse battery", h)


def test_verify_rejects_garbage():
    assert not auth.verify_password("x", "not-a-hash")
    assert not auth.verify_password("x", "md5$aa$bb")


def test_session_lifecycle():
    db = auth.SessionLocal()
    try:
        u = auth.User(
            username="sess-test",
            password_hash=auth.hash_password("whatever1"),
            role="viewer",
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        uid = u.id
    finally:
        db.close()

    token = auth.create_session(uid)
    assert auth.resolve_session(token)["username"] == "sess-test"
    auth.destroy_session(token)
    assert auth.resolve_session(token) is None
    assert auth.resolve_session(None) is None


def test_parse_demo_env(monkeypatch):
    monkeypatch.setenv(
        "DEMO_USERS", " demo:demo12345 , guest:guestpw99 ,bad:short, nocolon "
    )
    parsed = auth._parse_demo_env()
    assert parsed == {"demo": "demo12345", "guest": "guestpw99"}


def test_seed_demo_users_adds_and_prunes(monkeypatch):
    monkeypatch.setenv("DEMO_USERS", "demoA:demopass111,demoB:demopass222")
    auth.seed_demo_users()
    db = auth.SessionLocal()
    try:
        names = {u.username for u in db.query(auth.User).filter(auth.User.is_demo.is_(True))}
        assert names == {"demoA", "demoB"}
    finally:
        db.close()

    # drop demoB from the env -> it should be pruned, demoA kept
    monkeypatch.setenv("DEMO_USERS", "demoA:demopass111")
    auth.seed_demo_users()
    db = auth.SessionLocal()
    try:
        names = {u.username for u in db.query(auth.User).filter(auth.User.is_demo.is_(True))}
        assert names == {"demoA"}
    finally:
        db.close()
    monkeypatch.delenv("DEMO_USERS", raising=False)
    auth.seed_demo_users()


def test_throttle_trips_and_resets():
    auth._failures.clear()
    ip = "203.0.113.9"
    assert not auth._throttled(ip)
    for _ in range(auth._FAIL_MAX):
        auth._record_failure(ip)
    assert auth._throttled(ip)
    auth._failures.clear()
    assert not auth._throttled(ip)


# --------------------------------------------------------------------------
# integration: middleware + role gate against a live server
# --------------------------------------------------------------------------

def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def server():
    port = _free_port()
    env = {
        **os.environ,
        "DATA_DIR": tempfile.mkdtemp(prefix="auth-it-"),
        "OWNER_USERNAME": OWNER[0],
        "OWNER_PASSWORD": OWNER[1],
        "COOKIE_SECURE": "0",
        "DEMO_USERS": "demoguest:demoguest123",
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--port", str(port)],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(60):
            try:
                if requests.get(f"{base}/health", timeout=1).ok:
                    break
            except requests.RequestException:
                time.sleep(0.25)
        else:
            raise RuntimeError("test server did not start")
        yield base
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def _login(base, username, password) -> requests.Session:
    s = requests.Session()
    r = s.post(
        f"{base}/api/auth/login",
        json={"username": username, "password": password},
        timeout=5,
    )
    r.raise_for_status()
    return s


@pytest.fixture(scope="module")
def owner_session(server):
    return _login(server, *OWNER)


@pytest.fixture(scope="module")
def viewer_session(server, owner_session):
    owner_session.post(
        f"{server}/api/auth/users",
        json={"username": "pal", "password": "pal-pw-12345"},
        timeout=5,
    )
    return _login(server, "pal", "pal-pw-12345")


def test_health_is_public(server):
    assert requests.get(f"{server}/health", timeout=5).status_code == 200


def test_data_endpoints_401_without_session(server):
    for path in ("/dashboard", "/jobs", "/api/live-jobs", "/sync/status"):
        assert requests.get(f"{server}{path}", timeout=5).status_code == 401, path


def test_bad_login_401(server):
    r = requests.post(
        f"{server}/api/auth/login",
        json={"username": "owner", "password": "wrong"},
        timeout=5,
    )
    assert r.status_code == 401


def test_owner_reaches_everything(server, owner_session):
    for path in ("/dashboard", "/jobs", "/api/live-jobs", "/api/auth/users"):
        assert owner_session.get(f"{server}{path}", timeout=5).status_code == 200, path


def test_viewer_is_confined_to_live_jobs(server, viewer_session):
    assert viewer_session.get(f"{server}/api/live-jobs", timeout=5).status_code == 200
    assert (
        viewer_session.get(f"{server}/api/live-jobs/summary", timeout=5).status_code
        == 200
    )
    for blocked in ("/dashboard", "/jobs", "/jobs/1", "/sync/status", "/api/auth/users"):
        assert (
            viewer_session.get(f"{server}{blocked}", timeout=5).status_code == 403
        ), blocked
    assert viewer_session.post(f"{server}/sync", timeout=5).status_code == 403


def test_viewer_cannot_create_users(server, viewer_session):
    r = viewer_session.post(
        f"{server}/api/auth/users",
        json={"username": "x", "password": "yyyyyyyy"},
        timeout=5,
    )
    assert r.status_code == 403


def test_demo_user_from_env_can_sign_in_as_viewer(server):
    s = _login(server, "demoguest", "demoguest123")
    assert s.get(f"{server}/api/auth/me", timeout=5).json()["role"] == "viewer"
    assert s.get(f"{server}/api/live-jobs", timeout=5).status_code == 200
    assert s.get(f"{server}/dashboard", timeout=5).status_code == 403


def test_logout_invalidates_session(server):
    s = _login(server, *OWNER)
    assert s.get(f"{server}/dashboard", timeout=5).status_code == 200
    s.post(f"{server}/api/auth/logout", timeout=5)
    assert s.get(f"{server}/dashboard", timeout=5).status_code == 401
