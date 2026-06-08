from datetime import timedelta

import asyncpg

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.repositories.user_repository import get_user_by_email
from app.schemas.auth import LoginResponse, RoleEnum, UserOut


class InvalidCredentialsError(Exception):
    pass


async def login(
    conn: asyncpg.Connection[object],
    email: str,
    password: str,
    branch_id: int,
    remember_me: bool,
) -> LoginResponse:
    user = await get_user_by_email(conn, email)

    if user is None or not verify_password(password, user["password_hash"]):
        raise InvalidCredentialsError

    expires_minutes = (
        settings.access_token_remember_me_minutes
        if remember_me
        else settings.access_token_expire_minutes
    )

    token = create_access_token(
        payload={
            "sub": str(user["id"]),
            "email": user["email"],
            "role": user["role"],
            "branch_id": branch_id,
        },
        expires_delta=timedelta(minutes=expires_minutes),
    )

    return LoginResponse(
        token=token,
        expires_in=expires_minutes * 60,
        user=UserOut(
            id=user["id"],
            full_name=user["full_name"],
            email=user["email"],
            role=RoleEnum(user["role"]),
            branch_id=branch_id,
        ),
    )
