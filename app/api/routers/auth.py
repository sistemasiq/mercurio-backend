from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.auth import LoginRequest, LoginResponse, TokenData
from app.services.auth_service import InvalidCredentialsError, SucursalNoAsignadaError, login

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login_endpoint(
    body: LoginRequest,
    conn: asyncpg.Connection = Depends(get_db),
) -> LoginResponse:
    try:
        return await login(
            conn=conn,
            email=body.email,
            password=body.password,
            sucursal_id=body.sucursal_id,
            remember_me=body.remember_me,
        )
    except (InvalidCredentialsError, SucursalNoAsignadaError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Credenciales incorrectas."},
        ) from None


@router.post("/logout")
async def logout_endpoint(
    _current_user: TokenData = Depends(get_current_user),
) -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)
