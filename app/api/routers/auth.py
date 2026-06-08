from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.auth import LoginRequest, LoginResponse, TokenData
from app.services.auth_service import InvalidCredentialsError, login

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login_endpoint(
    body: LoginRequest,
    conn: asyncpg.Connection[Any] = Depends(get_db),
) -> LoginResponse:
    try:
        return await login(
            conn=conn,
            email=body.email,
            password=body.password,
            branch_id=body.branch_id,
            remember_me=body.remember_me,
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Credenciales incorrectas."},
        ) from None


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_endpoint(
    _current_user: TokenData = Depends(get_current_user),
) -> None:
    pass
