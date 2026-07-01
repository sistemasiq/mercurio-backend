from uuid import UUID

import asyncpg


async def nino_create(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    nombre: str,
    edad: int,
    notas: str | None,
    usuario_id: UUID,
) -> UUID:
    row = await conn.fetchrow(
        """
       INSERT INTO ninos (sucursal_id, nombre_completo, edad, notas, creado_por)
       VALUES ($1,$2,$3,$4,$5)
       RETURNING id
   """,
        sucursal_id,
        nombre,
        edad,
        notas,
        usuario_id,
    )

    return UUID(str(row["id"]))
