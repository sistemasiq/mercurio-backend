import asyncpg
from app.schemas.registros import OnboardingRequest
from fastapi import HTTPException,UploadFile
from datetime import datetime, timezone, timedelta
from uuid import UUID,uuid4
from app.core.storage import IDENTIFICACIONES_DIR, LLEGADAS_DIR

from app.repositories.estancias import get_activos_by_sucursal_id
from app.repositories.tutores import get_tutor_by_phone,tutor_create
from app.repositories.detalles_registro import insert_detalle_registro
from app.repositories.registros import registro_create
from app.repositories.ninos import nino_create
from app.repositories.pagos import pago_create
from app.repositories.productos import get_precio_individual_by_id,get_productos_estancia_by_sucursal_id
from app.repositories.registros import EstadoRegistro,change_registro_estado,registro_update_total

async def create_estancia(
       conn: asyncpg.Connection,
       data: OnboardingRequest,
       foto_ine: UploadFile,
       foto_llegada: UploadFile,
       usuario_id: UUID
   ):


       async with conn.transaction():
           # 1. tutor
           tutor = await get_tutor_by_phone(conn, data.tutor.telefono, data.sucursalId)
          
           if tutor:
               tutor_id = tutor["id"]
           else:
               tutor_id = await tutor_create(
                   conn,
                   data.sucursalId,
                   data.tutor.nombreCompleto,
                   data.tutor.telefono,
                   usuario_id
               )


           registro_id = uuid4()
          
           # --- GUARDAR FOTOS FÍSICAMENTE ---
           nombre_archivo = f"{registro_id}.jpg"
           ruta_fisica_ine = IDENTIFICACIONES_DIR / nombre_archivo
           ruta_fisica_llegada = LLEGADAS_DIR / nombre_archivo


           with open(ruta_fisica_ine, "wb") as f:
               f.write(await foto_ine.read())
          
           with open(ruta_fisica_llegada, "wb") as f:
               f.write(await foto_llegada.read())


           # Rutas relativas para guardar en BD
           ruta_bd_ine = f"uploads/identificaciones/{nombre_archivo}"
           ruta_bd_llegada = f"uploads/llegadas/{nombre_archivo}"


           # 2. registro (Un solo INSERT limpio)
           await registro_create(
               conn,
               registro_id,
               data.sucursalId,
               tutor_id,
               ruta_bd_ine,
               ruta_bd_llegada,
               usuario_id
           )


           total = 0


           # 3. detalles
           for d in data.detalles:


               nino_id = await nino_create(
                   conn,
                   data.sucursalId,
                   d.nino.nombreCompleto,
                   d.nino.edad,
                   d.nino.notas,
                   usuario_id
               )


               precio = await get_precio_individual_by_id(d.productoId)


               if precio is None:
                   raise HTTPException(400, "Producto inválido")
              
               entrada = datetime.now(timezone.utc)

               salida_esperada = entrada + timedelta(hours=d.cantidad)

               await insert_detalle_registro(
                    conn,
                    data.sucursalId,
                    registro_id,
                    nino_id,
                    d.pulseraId,
                    d.productoId,
                    d.cantidad,
                    precio,
                    data.parentesco,
                    entrada,
                    salida_esperada,
                    usuario_id
               )


               total += precio * d.cantidad


           # 4. pagos
           total_pagado = 0


           for p in data.pagos:
               await pago_create(
                   conn,
                   data.sucursalId,
                   registro_id,
                   p.metodoPagoId,
                   p.monto,
                   usuario_id
               )
               total_pagado += p.monto


           # 5. actualizar total
           await registro_update_total(conn, registro_id, total)


           # 6. activar si ya pagó todo
           if total_pagado >= total:
               await change_registro_estado(conn,EstadoRegistro.ACTIVO,registro_id)


           return {
               "registroId": registro_id,
               "total": total,
               "pagado": total_pagado,
               "estado": "A" if total_pagado >= total else "P"
           }


async def get_activos_estancia_by_sucursal_id(conn: asyncpg.Connection,sucursal_id: UUID):
    return get_activos_by_sucursal_id(conn,sucursal_id)

async def get_productos_estancia_by_id_sucursal(conn: asyncpg.Connection,sucursal_id: UUID):
    return get_productos_estancia_by_sucursal_id(conn,sucursal_id)