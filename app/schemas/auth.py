from datetime import datetime
from enum import Enum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RoleEnum(str, Enum):
    administrador_sistema = "AdministradorSistema"
    administrador = "Administrador"
    cajero = "Cajero"
    cocina = "Cocina"


class LoginRequest(BaseModel):
    sucursal_id: Annotated[UUID | None, Field(alias="sucursalId")] = None
    email: EmailStr
    password: str
    remember_me: Annotated[bool, Field(alias="rememberMe")] = False

    model_config = {"populate_by_name": True}


class RefreshRequest(BaseModel):
    refresh_token: Annotated[str, Field(alias="refreshToken")]

    model_config = {"populate_by_name": True}


class UserOut(BaseModel):
    id: UUID
    full_name: str
    email: str
    role: RoleEnum
    branch_id: UUID | None
    permissions: list[str] = []


class LoginResponse(BaseModel):
    requires_branch_selection: Literal[False] = False
    token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: str
    refresh_expires_in: int
    user: UserOut


class BranchOption(BaseModel):
    id: UUID
    nombre: str


class BranchSelectionRequired(BaseModel):
    """Respuesta de login cuando un Administrador con 2+ sucursales no indicó cuál usar."""

    requires_branch_selection: Literal[True] = True
    sucursales: list[BranchOption]


class TokenData(BaseModel):
    sub: str
    email: str
    role: RoleEnum
    branch_id: UUID | None
    permissions: list[str] = []
    jti: str
    exp: datetime
