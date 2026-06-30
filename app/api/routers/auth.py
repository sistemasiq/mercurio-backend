from datetime import UTC, datetime, timedelta
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Header, status

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    JWTError,
    crear_access_token,
    decodificar_token,
    generar_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.exceptions import CredencialesInvalidas
from app.repositories import refresh_token as refresh_repo
from app.repositories import tokens_revocados
from app.repositories import usuario as usuario_repo
from app.schemas.auth import LoginRequest, LoginResponse, RefreshRequest, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


async def _construir_respuesta(
    conn: asyncpg.Connection, usuario: asyncpg.Record, expires_minutes: int
) -> tuple[LoginResponse, str]:
    """Crea el access token y deja listo el refresh (devuelve también su hash)."""
    sucursal_id = await usuario_repo.obtener_sucursal_id(conn, usuario["id"])
    token, _, expires_in = crear_access_token(
        sub=str(usuario["id"]),
        email=usuario["email"],
        role=usuario["rol_nombre"],
        branch_id=str(sucursal_id) if sucursal_id else None,
        expires_minutes=expires_minutes,
    )
    refresh_plano, refresh_hash = generar_refresh_token()
    respuesta = LoginResponse(
        token=token,
        refreshToken=refresh_plano,
        expiresIn=expires_in,
        user=UserOut(
            id=usuario["id"],
            name=usuario["nombre_completo"],
            email=usuario["email"],
            role=usuario["rol_nombre"],
            branch_id=sucursal_id,
        ),
    )
    return respuesta, refresh_hash


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, conn: asyncpg.Connection = Depends(get_db)) -> LoginResponse:
    usuario = await usuario_repo.obtener_por_email(conn, body.email)
    if not usuario or not verify_password(body.password, usuario["password_hash"]):
        raise CredencialesInvalidas()

    expires_minutes = 60 * 24 if body.rememberMe else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    respuesta, refresh_hash = await _construir_respuesta(conn, usuario, expires_minutes)
    await refresh_repo.crear(
        conn,
        usuario_id=usuario["id"],
        token_hash=refresh_hash,
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return respuesta


@router.post("/refresh", response_model=LoginResponse)
async def refresh(
    body: RefreshRequest, conn: asyncpg.Connection = Depends(get_db)
) -> LoginResponse:
    token_hash = hash_refresh_token(body.refreshToken)
    registro = await refresh_repo.obtener_por_hash(conn, token_hash)
    if not registro or registro["revocado"] or registro["expires_at"] < datetime.now(UTC):
        raise CredencialesInvalidas()

    usuario = await usuario_repo.obtener_por_id(conn, registro["usuario_id"])
    if not usuario:
        raise CredencialesInvalidas()

    # Rotación: revoca el refresh usado y emite uno nuevo.
    await refresh_repo.revocar(conn, token_hash)
    respuesta, nuevo_hash = await _construir_respuesta(
        conn, usuario, settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    await refresh_repo.crear(
        conn,
        usuario_id=usuario["id"],
        token_hash=nuevo_hash,
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return respuesta


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    authorization: str = Header(default=""),
    conn: asyncpg.Connection = Depends(get_db),
) -> None:
    """Añade el jti del access token a la lista de revocados (best-effort)."""
    if not authorization.lower().startswith("bearer"):
        return
    token = authorization[len("bearer") :].strip()
    try:
        payload = decodificar_token(token)
    except JWTError:
        return
    jti = payload.get("jti")
    exp = payload.get("exp")
    if jti and exp:
        await tokens_revocados.agregar(
            conn, jti=UUID(jti), expires_at=datetime.fromtimestamp(exp, tz=UTC)
        )
