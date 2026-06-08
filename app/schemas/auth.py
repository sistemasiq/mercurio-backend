from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class RoleEnum(str, Enum):
    administrador = "Administrador"
    cajero = "Cajero"
    cocina = "Cocina"


class LoginRequest(BaseModel):
    branch_id: int = Field(alias="branchId")
    email: EmailStr
    password: str
    remember_me: bool = Field(default=False, alias="rememberMe")

    model_config = {"populate_by_name": True}


class UserOut(BaseModel):
    id: int
    full_name: str
    email: str
    role: RoleEnum
    branch_id: int


class LoginResponse(BaseModel):
    token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserOut


class TokenData(BaseModel):
    sub: str
    email: str
    role: RoleEnum
    branch_id: int
