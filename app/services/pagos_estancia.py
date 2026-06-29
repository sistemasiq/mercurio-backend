import asyncpg
from uuid import UUID
from typing import List
from app.schemas.pagos import PagoIn
from fastapi import HTTPException

from app.repositories.registros import exists_registro
from app.repositories.pagos import pago_create


async def pago_create_service(
       conn: asyncpg.Connection,
       data: List[PagoIn],
       sucursal_id: UUID,
       registro_id: UUID,
       usuario_id: UUID,
   ):
      
       registro = await exists_registro(conn,registro_id)


       if registro:
           for pago in data:
               await pago_create(
                   conn,
                   sucursal_id,
                   registro_id,
                   pago.metodoPagoId,
                   pago.monto,
                   usuario_id,
               )
       else:
           raise HTTPException(404, "Registro no encontrado")
