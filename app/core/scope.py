"""Alcance de sucursal derivado del usuario autenticado.

Antes duplicado de forma idéntica en app/services/estancias.py y
app/services/comanda_service.py; centralizado aquí para reutilizarlo en
cualquier endpoint que deba filtrar por sucursal (ver T2 en
TICKETS_E2E.md).
"""

from app.core.roles import ROL_SISTEMA
from app.schemas.auth import TokenData

VE_TODAS_LAS_SUCURSALES = None


def sucursal_scope(current_user: TokenData) -> str | None:
    """Sucursal a la que debe limitarse current_user, o VE_TODAS_LAS_SUCURSALES
    (None) si el rol ve todas las sucursales (AdministradorSistema). Si el
    usuario no es AdministradorSistema y no tiene sucursal asignada, devuelve
    un id que no existe para que el filtro no traiga nada, en vez de
    reventar.

    AdministradorSistema puede "pararse" en una sucursal específica (header
    X-Sucursal-Vista, resuelto en get_current_user) -- en ese caso branch_id
    ya viene poblado en el token y se filtra igual que cualquier otro rol."""
    if current_user.role == ROL_SISTEMA and current_user.branch_id is None:
        return VE_TODAS_LAS_SUCURSALES
    if current_user.branch_id is None:
        return "00000000-0000-0000-0000-000000000000"
    return str(current_user.branch_id)
