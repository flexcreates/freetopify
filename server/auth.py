from __future__ import annotations

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

import aiosqlite
import logging
import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import JSONResponse, Response

from server.models import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=True)

logger = logging.getLogger("server.auth")

# Max 10 attempts per minute per IP.
_LOGIN_WINDOW_SECONDS = 60
_LOGIN_MAX_ATTEMPTS = 10
_login_attempts: dict[str, deque[float]] = defaultdict(deque)


def _check_login_rate_limit(ip: str) -> None:
    now = datetime.now(UTC).timestamp()
    q = _login_attempts[ip]
    while q and (now - q[0]) > _LOGIN_WINDOW_SECONDS:
        q.popleft()
    if len(q) >= _LOGIN_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many login attempts")
    q.append(now)
    logger.debug("Login attempts for %s: %d", ip, len(q))


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(secret_key: str, subject: str, expire_hours: int, extra_claims: dict | None = None) -> tuple[str, int]:
    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=expire_hours)
    payload = {"sub": subject, "iat": int(now.timestamp()), "exp": int(expires_at.timestamp())}
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token, int(timedelta(hours=expire_hours).total_seconds())


def decode_access_token(secret_key: str, token: str) -> dict:
    try:
        return jwt.decode(token, secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


async def ensure_default_admin(database_path: str, username: str, password: str) -> None:
    """Upsert the admin user on every server start.

    This means changing ADMIN_USERNAME / ADMIN_PASSWORD in .env and
    restarting the server immediately invalidates all old tokens — the
    old username no longer exists in the DB so its JWT is rejected.
    """
    new_hash = hash_password(password)
    async with aiosqlite.connect(database_path) as db:
        # If table is empty, insert fresh.
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total = (await cursor.fetchone())[0]
        if total == 0:
            await db.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, new_hash),
            )
        else:
            # Always update the first admin row to match current .env credentials.
            # If the username changed, the old row is deleted and the new one inserted
            # so that any JWT issued under the old username becomes invalid.
            cursor = await db.execute("SELECT username FROM users LIMIT 1")
            existing_row = await cursor.fetchone()
            existing_username = existing_row[0] if existing_row else None

            if existing_username != username:
                # Username changed — remove old row, insert new one.
                # Old JWTs carried the old sub and will now fail the DB check.
                await db.execute("DELETE FROM users WHERE username = ?", (existing_username,))
                await db.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, new_hash),
                )
                logger.info(
                    "Admin username changed %s → %s; all prior sessions invalidated",
                    existing_username, username,
                )
            else:
                # Username unchanged — still re-hash and update the password so a
                # password change in .env is reflected immediately on restart.
                await db.execute(
                    "UPDATE users SET password_hash = ? WHERE username = ?",
                    (new_hash, username),
                )
        await db.commit()


async def get_current_user(request: Request) -> str:
    return await get_current_user_from_request_allow_guest(request, allow_guest=False)


async def get_current_user_allow_guest(request: Request) -> str:
    return await get_current_user_from_request_allow_guest(request, allow_guest=True)


async def get_current_user_from_request(request: Request, token_query: str | None = None) -> str:
    return await get_current_user_from_request_allow_guest(request, token_query=token_query, allow_guest=False)


async def get_current_user_from_request_allow_guest(
    request: Request,
    token_query: str | None = None,
    allow_guest: bool = True,
) -> str:
    token = token_query
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
    if not token:
        token = request.cookies.get("freetopify_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    settings = request.app.state.settings
    payload = decode_access_token(settings.secret_key, token)
    subject = payload.get("sub")
    if not allow_guest and payload.get("role") == "guest":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Guest access not permitted")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    # Validate admin tokens against the DB — invalidates sessions after credential rotation.
    if payload.get("role") != "guest":
        async with aiosqlite.connect(str(settings.database_path)) as db:
            cursor = await db.execute("SELECT 1 FROM users WHERE username = ?", (subject,))
            if not await cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalidated — please log in again")
    return str(subject)


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, request: Request) -> Response:
    client = request.client.host if request.client else "unknown"
    _check_login_rate_limit(client)

    settings = request.app.state.settings
    async with aiosqlite.connect(str(settings.database_path)) as db:
        cursor = await db.execute(
            "SELECT username, password_hash FROM users WHERE username = ?",
            (body.username,),
        )
        row = await cursor.fetchone()

    if not row or not verify_password(body.password, row[1]):
        logger.info("Failed login attempt for username=%s from=%s", body.username, client)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    token, expires_in = create_access_token(settings.secret_key, row[0], settings.token_expire_hours)
    response = JSONResponse(LoginResponse(access_token=token, expires_in=expires_in).model_dump())
    response.set_cookie(
        key="freetopify_token",
        value=token,
        max_age=expires_in,
        path="/",
        samesite="lax",
        httponly=True,
    )
    return response


@router.post("/guest", response_model=LoginResponse)
async def guest_join(body: LoginRequest | dict, request: Request) -> Response:
    client = request.client.host if request.client else "unknown"
    _check_login_rate_limit(client)
    # Accept either a GuestRequest or raw dict to stay backwards compatible with clients
    name = None
    pin = None
    if hasattr(body, "name") and hasattr(body, "pin"):
        name = getattr(body, "name")
        pin = getattr(body, "pin")
    elif isinstance(body, dict):
        name = body.get("name")
        pin = body.get("pin")
    else:
        # Fallback: try to read as LoginRequest fields
        name = getattr(body, "username", None)
        pin = getattr(body, "password", None)

    if not name or not pin:
        logger.info("Bad guest join request from=%s missing fields", client)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing name or pin")

    settings = request.app.state.settings
    if not settings.guest_pin:
        logger.info("Guest join attempt when guest access disabled from=%s name=%s", client, name)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Guest access not enabled")
    if pin != settings.guest_pin:
        logger.info("Invalid guest PIN attempt from=%s name=%s", client, name)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid PIN")

    subject = f"guest:{name}"
    ttl = getattr(settings, "guest_token_expire_hours", settings.token_expire_hours)
    token, expires_in = create_access_token(settings.secret_key, subject, ttl, extra_claims={"role": "guest"})
    logger.info("Guest token issued for name=%s from=%s ttl_hours=%s", name, client, ttl)
    response = JSONResponse(LoginResponse(access_token=token, expires_in=expires_in).model_dump())
    response.set_cookie(
        key="freetopify_token",
        value=token,
        max_age=expires_in,
        path="/",
        samesite="lax",
        httponly=True,
    )
    return response


@router.get("/me")
async def me(current_user: str = Depends(get_current_user_allow_guest)) -> dict[str, str]:
    return {"username": current_user}


@router.post("/logout")
async def logout(current_user: str = Depends(get_current_user_allow_guest)) -> dict[str, str]:
    response = JSONResponse({"status": "ok", "user": current_user})
    response.delete_cookie(key="freetopify_token", path="/")
    return response
