from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg

from app.repositories import extras as extras_repo
from app.repositories import reservacion_extras as reservacion_extras_repo
from app.repositories import reservaciones as reservaciones_repo


class ReservaRepositoryAsyncpg:
    """Adaptador del puerto ``ReservaRepository`` sobre asyncpg.

    No escribe SQL directamente: delega en la capa ``app/repositories`` (única
    capa con SQL), respetando la regla de capas del proyecto.
    """

    def __init__(self, conn: asyncpg.Connection) -> None:
        self.conn = conn

    async def obtener_reservacion(self, reservacion_id: UUID) -> dict[str, Any] | None:
        row = await reservaciones_repo.obtener_por_id(self.conn, reservacion_id)
        return dict(row) if row else None

    async def obtener_extra(self, extra_id: UUID) -> dict[str, Any] | None:
        row = await extras_repo.obtener_por_id(self.conn, extra_id)
        return dict(row) if row else None

    async def agregar_extra_a_reserva(
        self,
        *,
        reservacion_id: UUID,
        extra_id: UUID,
        cantidad: int,
        precio_unitario: Decimal,
        creado_por: UUID | None,
    ) -> dict[str, Any]:
        row = await reservacion_extras_repo.crear(
            self.conn,
            reservacion_id=reservacion_id,
            extra_id=extra_id,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            creado_por=creado_por,
        )
        return dict(row)
