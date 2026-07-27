from uuid import UUID

import asyncpg

from app.core.roles import ROL_SISTEMA
from app.exceptions import DatosInvalidos, NoEncontrado
from app.repositories import lealtad_repository
from app.schemas.auth import TokenData
from app.schemas.lealtad import ConfiguracionLealtadBase, ConfiguracionLealtadOut


def resolver_sucursal(current_user: TokenData, sucursal_id: UUID | None) -> UUID:
    """AdministradorSistema ve todas las sucursales, así que debe indicar
    explícitamente cuál configurar/consultar. El resto usa su sucursal activa."""
    if current_user.role == ROL_SISTEMA:
        if sucursal_id is None:
            raise DatosInvalidos("Debes indicar sucursal_id (AdministradorSistema ve todas).")
        return sucursal_id
    if current_user.branch_id is None:
        raise DatosInvalidos("La sesión no tiene una sucursal activa.")
    return current_user.branch_id


async def obtener_configuracion(
    conn: asyncpg.Connection, current_user: TokenData, sucursal_id: UUID | None
) -> ConfiguracionLealtadOut:
    scope = resolver_sucursal(current_user, sucursal_id)
    row = await lealtad_repository.obtener_configuracion(conn, scope)
    if not row:
        raise NoEncontrado("Configuración de lealtad")
    return ConfiguracionLealtadOut.model_validate(row)


async def actualizar_configuracion(
    conn: asyncpg.Connection,
    current_user: TokenData,
    sucursal_id: UUID | None,
    body: ConfiguracionLealtadBase,
) -> ConfiguracionLealtadOut:
    scope = resolver_sucursal(current_user, sucursal_id)
    row = await lealtad_repository.upsert_configuracion(
        conn,
        scope,
        porcentaje_retorno=body.porcentaje_retorno,
        dias_caducidad=body.dias_caducidad,
        valor_punto=body.valor_punto,
        activo=body.activo,
        usuario_id=UUID(current_user.sub),
    )
    return ConfiguracionLealtadOut.model_validate(row)
