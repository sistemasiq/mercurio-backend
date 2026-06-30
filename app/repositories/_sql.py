"""Helpers internos para construir SQL parametrizado en los repositorios.

Los nombres de tabla/columna se interpolan (provienen del código, nunca del
cliente); los valores siempre viajan como parámetros ``$1, $2, ...``.
"""

from typing import Any


def build_update(
    tabla: str,
    cambios: dict[str, Any],
    *,
    id_col: str = "id",
    id_val: Any,
    touch_modificado: bool = True,
    modificado_por: Any = None,
) -> tuple[str, list[Any]]:
    """Arma un ``UPDATE ... SET ... WHERE id_col = $n RETURNING *``.

    ``cambios`` mapea columna -> nuevo valor. Si ``touch_modificado`` añade
    ``modificado = now()`` y, si se pasa, ``modificado_por``.
    """
    sets: list[str] = []
    args: list[Any] = []
    i = 1
    for col, val in cambios.items():
        sets.append(f"{col} = ${i}")
        args.append(val)
        i += 1
    if touch_modificado:
        sets.append("modificado = now()")
        if modificado_por is not None:
            sets.append(f"modificado_por = ${i}")
            args.append(modificado_por)
            i += 1
    args.append(id_val)
    query = f"UPDATE public.{tabla} SET {', '.join(sets)} WHERE {id_col} = ${i} RETURNING *"
    return query, args
