from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def create_access_token(payload: dict[str, object], expires_delta: timedelta) -> str:
    now = datetime.now(UTC)
    data = {**payload, "iat": now, "exp": now + expires_delta}
    return jwt.encode(data, settings.secret_key, algorithm=settings.algorithm)  # type: ignore[no-any-return]


def decode_access_token(token: str) -> dict[str, object]:
    """Decodifica el JWT y devuelve el payload. Lanza JWTError si es inválido o expirado."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])  # type: ignore[no-any-return]
    except JWTError as exc:
        raise exc
