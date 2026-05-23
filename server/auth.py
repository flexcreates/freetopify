from __future__ import annotations

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

import aiosqlite
import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from server.models import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=True)

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


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(secret_key: str, subject: str, expire_hours: int) -> tuple[str, int]:
    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=expire_hours)
    payload = {"sub": subject, "iat": int(now.timestamp()), "exp": int(expires_at.timestamp())}
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token, int(timedelta(hours=expire_hours).total_seconds())


def decode_access_token(secret_key: str, token: str) -> dict:
    try:
        return jwt.decode(token, secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


async def ensure_default_admin(database_path: str, username: str, password: str) -> None:
    async with aiosqlite.connect(database_path) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total = (await cursor.fetchone())[0]
        if total == 0:
            await db.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, hash_password(password)),
            )
            await db.commit()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    token = credentials.credentials
    settings = request.app.state.settings
    payload = decode_access_token(settings.secret_key, token)
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    return str(subject)


def get_current_user_from_request(request: Request, token_query: str | None = None) -> str:
    token = token_query
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    payload = decode_access_token(request.app.state.settings.secret_key, token)
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    return str(subject)


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, request: Request) -> LoginResponse:
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    token, expires_in = create_access_token(settings.secret_key, row[0], settings.token_expire_hours)
    return LoginResponse(access_token=token, expires_in=expires_in)


@router.get("/me")
async def me(current_user: str = Depends(get_current_user)) -> dict[str, str]:
    return {"username": current_user}


@router.post("/logout")
async def logout(current_user: str = Depends(get_current_user)) -> dict[str, str]:
    return {"status": "ok", "user": current_user}
