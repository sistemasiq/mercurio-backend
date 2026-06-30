import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Genera el hash bcrypt de una contraseña en texto plano."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verifica una contraseña en texto plano contra su hash bcrypt."""
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def crear_access_token(
    *,
    sub: str,
    email: str,
    role: str,
    branch_id: str | None,
    expires_minutes: int | None = None,
) -> tuple[str, str, int]:
    """Crea un JWT de acceso. Devuelve (token, jti, expires_in_segundos)."""
    minutos = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    jti = str(uuid4())
    expira = datetime.now(UTC) + timedelta(minutes=minutos)
    payload = {
        "sub": sub,
        "email": email,
        "role": role,
        "branch_id": branch_id,
        "jti": jti,
        "exp": expira,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti, minutos * 60


def decodificar_token(token: str) -> dict[str, Any]:
    """Decodifica y valida un JWT. Lanza JWTError si es inválido o expiró."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def generar_refresh_token() -> tuple[str, str]:
    """Genera un refresh token. Devuelve (token_plano, hash_sha256)."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    """Hash SHA-256 de un refresh token para almacenarlo en la DB."""
    return hashlib.sha256(raw.encode()).hexdigest()


__all__ = [
    "hash_password",
    "verify_password",
    "crear_access_token",
    "decodificar_token",
    "generar_refresh_token",
    "hash_refresh_token",
    "JWTError",
]
