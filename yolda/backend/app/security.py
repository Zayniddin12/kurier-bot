import hashlib
import secrets
import string
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings

ALG = "HS256"
_ALNUM = string.ascii_letters + string.digits


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode()[:72], h.encode())
    except ValueError:
        return False


def create_token(sub: str, kind: str = "user", minutes: int | None = None) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": sub, "kind": kind, "exp": exp}, settings.SECRET_KEY, algorithm=ALG)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALG])
    except JWTError:
        return None


def new_api_key() -> tuple[str, str, str]:
    """(to'liq kalit, prefiks, hash)"""
    key = "yl_live_" + "".join(secrets.choice(_ALNUM) for _ in range(32))
    return key, key[:12], hash_key(key)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def new_webhook_secret() -> str:
    return "whsec_" + "".join(secrets.choice(_ALNUM) for _ in range(32))
