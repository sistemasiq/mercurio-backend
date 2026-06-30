from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    rememberMe: bool = False


class RefreshRequest(BaseModel):
    refreshToken: str = Field(..., min_length=1)


class UserOut(BaseModel):
    id: UUID
    name: str
    email: str
    role: str
    branch_id: UUID | None = None


class LoginResponse(BaseModel):
    token: str
    refreshToken: str
    expiresIn: int
    user: UserOut


class TokenData(BaseModel):
    """Datos extraídos del JWT de acceso ya verificado."""

    sub: UUID
    email: str
    role: str
    branch_id: UUID | None = None
    jti: UUID
