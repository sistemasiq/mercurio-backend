from uuid import UUID
import asyncpg


async def pago_create(
   conn: asyncpg.Connection,
   sucursal_id: UUID,
   registro_id: UUID,
   metodo_pago_id: UUID,
   monto: float,
   usuario_id: UUID,
):
   await conn.execute("""
       INSERT INTO pagos_estancia (
           sucursal_id,
           registros_id,
           metodos_pago_id,
           monto,
           creado_por
       )
       VALUES ($1,$2,$3,$4,$5)
   """, sucursal_id, registro_id, metodo_pago_id, monto, usuario_id)
