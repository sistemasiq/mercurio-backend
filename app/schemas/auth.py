from enum import Enum
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RoleEnum(str, Enum):
    administrador_sistema = "AdministradorSistema"
    administrador = "Administrador"
    cajero = "Cajero"
    cocina = "Cocina"


class LoginRequest(BaseModel):
    sucursal_id: UUID | None = Field(default=None, alias="sucursalId")
    email: EmailStr
    password: str
    remember_me: bool = Field(default=False, alias="rememberMe")

    model_config = {"populate_by_name": True}


class UserOut(BaseModel):
    id: UUID
    nombre_completo: str
    email: str
    rol: RoleEnum
    sucursal_id: UUID | None


class LoginResponse(BaseModel):
    token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserOut


class TokenData(BaseModel):
    sub: str
    email: str
    rol: RoleEnum
    sucursal_id: UUID | None
