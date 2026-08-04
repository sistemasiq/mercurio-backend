"""
app/schemas/horarios_cajas.py
Schemas Pydantic para los CRUDs administrativos de horarios (turnos) y cajas.
"""

from __future__ import annotations

from pydantic import BaseModel


# ── Horarios (turnos de trabajo) ──────────────────────────────────────────────


class HorarioCreate(BaseModel):
    nombre: str
    hora_inicio: str  # "HH:MM"
    hora_fin: str     # "HH:MM"


class HorarioUpdate(BaseModel):
    nombre: str | None = None
    hora_inicio: str | None = None
    hora_fin: str | None = None
    activo: bool | None = None


class HorarioResponse(BaseModel):
    id: str
    nombre: str
    hora_inicio: str
    hora_fin: str
    activo: bool


# ── Cajas físicas (gestión administrativa) ────────────────────────────────────


class CajaAdminCreate(BaseModel):
    nombre: str
    numero: int


class CajaAdminUpdate(BaseModel):
    nombre: str | None = None
    numero: int | None = None
    activo: bool | None = None


class CajaAdminResponse(BaseModel):
    id: str
    nombre: str
    numero: int
    activo: bool
