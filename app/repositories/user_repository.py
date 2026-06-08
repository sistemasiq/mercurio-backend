from typing import Any, TypedDict

import asyncpg


class UserRecord(TypedDict):
    id: int
    email: str
    password_hash: str
    full_name: str
    role: str
    branch_id: int
    is_active: bool


# TODO: conectar cuando el esquema esté definido.
# Tabla esperada:
#   users(id, email, password_hash, full_name, role, branch_id, is_active, created_at)
async def get_user_by_email(conn: asyncpg.Connection[Any], email: str) -> UserRecord | None:
    row = await conn.fetchrow(
        """
        SELECT id, email, password_hash, full_name, role, branch_id, is_active
        FROM users
        WHERE email = $1 AND is_active = true
        """,
        email,
    )
    if row is None:
        return None
    return UserRecord(
        id=row["id"],
        email=row["email"],
        password_hash=row["password_hash"],
        full_name=row["full_name"],
        role=row["role"],
        branch_id=row["branch_id"],
        is_active=row["is_active"],
    )
