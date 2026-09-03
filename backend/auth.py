"""Session-based auth for the tracker.

The app has one **owner** (that's you - seeded from ``OWNER_USERNAME`` /
``OWNER_PASSWORD``, or the legacy ``BASIC_AUTH_USER`` / ``BASIC_AUTH_PASS``)
and any number of **viewer** accounts the owner creates in Settings.
Viewers can only reach the Live Jobs endpoints - the middleware in
``main.py`` 403s them everywhere else, so synced email never leaves the
owner's session.

No external dependencies: passwords are ``hashlib.scrypt`` hashes and
sessions are opaque tokens in a DB table (revocable, survive a restart,
no signing key to manage).
"""

from __future__ import annotations

import hmac
import os
import secrets
import time
from datetime import datetime, timedelta
from hashlib import scrypt

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, StringConstraints
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db import SessionLocal, engine
from db_base import Base

SESSION_TTL = timedelta(days=30)
COOKIE_NAME = "jt_session"

# scrypt work factors - RFC 7914 interactive-login range
_SCRYPT = dict(n=2**14, r=8, p=1, dklen=32, maxmem=64 * 1024 * 1024)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="viewer")
    is_disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # seeded from the DEMO_USERS env var rather than created by the owner
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


Base.metadata.create_all(bind=engine)


def _migrate() -> None:
    """create_all() never alters an existing table. ``is_demo`` was added
    to ``users`` after the table already shipped, so older deployments
    need a manual ALTER. Safe to run every boot - a duplicate-column
    error is swallowed."""
    from sqlalchemy import text

    with engine.begin() as conn:
        try:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN is_demo "
                    "BOOLEAN NOT NULL DEFAULT 0"
                )
            )
        except Exception:
            pass


_migrate()


# --------------------------------------------------------------------------
# passwords
# --------------------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = scrypt(password.encode("utf-8"), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt_hex, digest_hex = stored.split("$")
        if algo != "scrypt":
            return False
        digest = scrypt(
            password.encode("utf-8"), salt=bytes.fromhex(salt_hex), **_SCRYPT
        )
    except Exception:
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


# --------------------------------------------------------------------------
# owner seeding
# --------------------------------------------------------------------------

def _owner_env() -> tuple[str | None, str | None]:
    user = os.getenv("OWNER_USERNAME") or os.getenv("BASIC_AUTH_USER")
    password = os.getenv("OWNER_PASSWORD") or os.getenv("BASIC_AUTH_PASS")
    return user, password


def auth_configured() -> bool:
    """Auth is only enforced once an owner credential is configured -
    keeps local dev (no env) a no-op, exactly like the old Basic gate."""
    user, password = _owner_env()
    return bool(user and password)


def seed_owner() -> None:
    user, password = _owner_env()
    if not user or not password:
        return

    db = SessionLocal()
    try:
        row = db.query(User).filter(User.username == user).first()
        if row is None:
            db.add(
                User(
                    username=user,
                    password_hash=hash_password(password),
                    role="owner",
                )
            )
        else:
            # keep the owner row in step with the env every boot
            row.role = "owner"
            row.is_disabled = False
            if not verify_password(password, row.password_hash):
                row.password_hash = hash_password(password)
        db.commit()
    finally:
        db.close()


def _parse_demo_env() -> dict[str, str]:
    """DEMO_USERS="alice:pw12345678,bob:hunter2hunter" -> {name: password}.

    These are shareable read-only logins for showing the Live Jobs page
    off. They're viewer accounts like any other, just managed by the env
    instead of the Settings UI.
    """
    raw = os.getenv("DEMO_USERS", "")
    out: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        name, _, password = pair.partition(":")
        name, password = name.strip(), password.strip()
        if len(name) >= 2 and len(password) >= 8:
            out[name] = password
    return out


def seed_demo_users() -> None:
    wanted = _parse_demo_env()
    db = SessionLocal()
    try:
        # env is the source of truth for demo accounts: drop any that
        # were seeded before and are no longer listed (manual viewers,
        # is_demo=False, are never touched here).
        for row in db.query(User).filter(User.is_demo.is_(True)).all():
            if row.username not in wanted:
                db.query(AuthSession).filter(
                    AuthSession.user_id == row.id
                ).delete()
                db.delete(row)

        for name, password in wanted.items():
            row = db.query(User).filter(User.username == name).first()
            if row is None:
                db.add(
                    User(
                        username=name,
                        password_hash=hash_password(password),
                        role="viewer",
                        is_demo=True,
                    )
                )
            elif row.role != "owner":
                row.role = "viewer"
                row.is_demo = True
                row.is_disabled = False
                if not verify_password(password, row.password_hash):
                    row.password_hash = hash_password(password)
        db.commit()
    finally:
        db.close()


if auth_configured():
    seed_owner()
    seed_demo_users()


# --------------------------------------------------------------------------
# sessions
# --------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.utcnow()


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    db = SessionLocal()
    try:
        db.add(
            AuthSession(
                token=token,
                user_id=user_id,
                created_at=_utcnow(),
                expires_at=_utcnow() + SESSION_TTL,
            )
        )
        # opportunistic cleanup of anything long expired
        db.query(AuthSession).filter(
            AuthSession.expires_at < _utcnow() - timedelta(days=1)
        ).delete()
        db.commit()
    finally:
        db.close()
    return token


def destroy_session(token: str | None) -> None:
    if not token:
        return
    db = SessionLocal()
    try:
        db.query(AuthSession).filter(AuthSession.token == token).delete()
        db.commit()
    finally:
        db.close()


def resolve_session(token: str | None) -> dict | None:
    """Return ``{"id", "username", "role"}`` for a live session, else None."""
    if not token:
        return None
    db = SessionLocal()
    try:
        row = db.get(AuthSession, token)
        if row is None or row.expires_at < _utcnow():
            return None
        user = db.get(User, row.user_id)
        if user is None or user.is_disabled:
            return None
        return {"id": user.id, "username": user.username, "role": user.role}
    finally:
        db.close()


def cookie_is_secure(request: Request) -> bool:
    forced = os.getenv("COOKIE_SECURE")
    if forced in {"0", "1"}:
        return forced == "1"
    return (
        request.url.scheme == "https"
        or request.headers.get("x-forwarded-proto", "") == "https"
    )


# --------------------------------------------------------------------------
# login throttle (in-memory, per client IP)
# --------------------------------------------------------------------------

_FAIL_WINDOW = 300  # seconds
_FAIL_MAX = 8
_failures: dict[str, list[float]] = {}


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "?"


def _throttled(ip: str) -> bool:
    now = time.time()
    hits = [t for t in _failures.get(ip, []) if now - t < _FAIL_WINDOW]
    _failures[ip] = hits
    return len(hits) >= _FAIL_MAX


def _record_failure(ip: str) -> None:
    _failures.setdefault(ip, []).append(time.time())


# --------------------------------------------------------------------------
# routes
# --------------------------------------------------------------------------

router = APIRouter(prefix="/api/auth", tags=["auth"])

Username = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=2, max_length=60)
]
Password = Annotated[str, StringConstraints(min_length=8, max_length=200)]


class LoginBody(BaseModel):
    username: str
    password: str


class NewUserBody(BaseModel):
    username: Username
    password: Password


_DEV_USER = {"id": 0, "username": "dev", "role": "owner"}


def current_user(request: Request) -> dict:
    # no owner configured -> auth is disabled (local dev); treat the
    # caller as the owner so the SPA renders the full app.
    if not auth_configured():
        return _DEV_USER
    user = resolve_session(request.cookies.get(COOKIE_NAME))
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_owner(request: Request) -> dict:
    user = current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner only")
    return user


@router.post("/login")
def login(body: LoginBody, request: Request, response: Response):
    ip = _client_ip(request)
    if _throttled(ip):
        raise HTTPException(
            status_code=429, detail="Too many attempts - wait a few minutes"
        )

    db = SessionLocal()
    try:
        user = (
            db.query(User)
            .filter(User.username == body.username, User.is_disabled.is_(False))
            .first()
        )
        ok = user is not None and verify_password(body.password, user.password_hash)
        if not ok:
            _record_failure(ip)
            raise HTTPException(status_code=401, detail="Invalid username or password")

        token = create_session(user.id)
        response.set_cookie(
            COOKIE_NAME,
            token,
            max_age=int(SESSION_TTL.total_seconds()),
            httponly=True,
            samesite="lax",
            secure=cookie_is_secure(request),
            path="/",
        )
        _failures.pop(ip, None)
        return {"username": user.username, "role": user.role}
    finally:
        db.close()


@router.post("/logout")
def logout(request: Request, response: Response):
    destroy_session(request.cookies.get(COOKIE_NAME))
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
def me(request: Request):
    return current_user(request)


@router.get("/users")
def list_users(_: dict = Depends(require_owner)):
    db = SessionLocal()
    try:
        rows = db.query(User).order_by(User.created_at).all()
        return [
            {
                "id": u.id,
                "username": u.username,
                "role": u.role,
                "is_disabled": u.is_disabled,
                "is_demo": u.is_demo,
                "created_at": u.created_at.isoformat(),
            }
            for u in rows
        ]
    finally:
        db.close()


@router.post("/users", status_code=201)
def create_user(body: NewUserBody, _: dict = Depends(require_owner)):
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == body.username).first():
            raise HTTPException(status_code=409, detail="Username already taken")
        user = User(
            username=body.username,
            password_hash=hash_password(body.password),
            role="viewer",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"id": user.id, "username": user.username, "role": user.role}
    finally:
        db.close()


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, owner: dict = Depends(require_owner)):
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="No such user")
        if user.role == "owner" or user.id == owner["id"]:
            raise HTTPException(status_code=400, detail="Cannot remove the owner")
        db.query(AuthSession).filter(AuthSession.user_id == user_id).delete()
        db.delete(user)
        db.commit()
    finally:
        db.close()
