from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, StringConstraints

NombreRequerido = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

# PIN de caja (C1): 4 dígitos numéricos, igual que valida el front.
PinCaja = Annotated[str, StringConstraints(pattern=r"^\d{4}$")]


class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: NombreRequerido
    apellidos: str | None = None
    telefono: str | None = Field(default=None, max_length=20)
    password: str = Field(..., min_length=1)
    role: str
    branch_id: UUID | None = None
    pin: PinCaja | None = None


class UserUpdateRequest(BaseModel):
    email: EmailStr
    full_name: NombreRequerido
    apellidos: str | None = None
    telefono: str | None = Field(default=None, max_length=20)
    role: str
    branch_id: UUID | None = None
    password: str | None = None  # None = no cambiar
    is_active: bool | None = None  # None = no cambiar
    pin: PinCaja | None = None  # None = no cambiar


class UserResponse(BaseModel):
    id: UUID
    full_name: str
    apellidos: str | None = None
    telefono: str | None = None
    email: str
    role: str
    branch_id: UUID | None
    is_active: bool
    ultimo_acceso: datetime | None = None
    tiene_pin: bool = False


class CambiarMiPinRequest(BaseModel):
    """PUT /usuarios/me/pin — el usuario cambia su propio PIN de caja.

    `actual` acepta el PIN vigente o, si el usuario aún no tiene PIN
    configurado, su contraseña (decisión C1: "mientras el usuario no tenga
    PIN, se acepta su contraseña, igual que en el cierre").
    """

    actual: str = Field(..., min_length=1)
    pin_nuevo: PinCaja


class CambiarMiPinResponse(BaseModel):
    ok: bool
    tiene_pin: bool = True
