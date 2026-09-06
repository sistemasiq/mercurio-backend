from decimal import Decimal
from uuid import UUID

from app.exceptions import DatosInvalidos


def validar_cambio(
    pagos: list[tuple[UUID, Decimal]],
    cambio: Decimal,
    ids_metodos_efectivo: set[UUID],
) -> None:
    """Única fuente de verdad de "¿este cambio está respaldado por efectivo
    real?", reusada por completar_pago (POS), pagos_reservacion.completar()
    y estancias.create_estancia(). `pagos` es la lista (metodo_pago_id, monto)
    de la transacción en curso; `ids_metodos_efectivo` son los ids de
    metodos_pago cuyo tipo == 'E' (ver metodos_pago_repository.
    obtener_ids_por_tipo) -- nunca el nombre, que es editable.

    Un pago con tarjeta/transferencia no puede generar salida de efectivo:
    si el cambio declarado excede lo que efectivamente se pagó en métodos de
    tipo 'E', se rechaza, sin importar que el excedente agregado (todos los
    métodos juntos) sí alcance."""
    if cambio <= 0:
        return
    total_efectivo = sum(
        (monto for metodo_id, monto in pagos if metodo_id in ids_metodos_efectivo),
        Decimal("0"),
    )
    if cambio > total_efectivo:
        raise DatosInvalidos(
            f"El cambio declarado ({cambio}) excede el efectivo entregado "
            f"({total_efectivo}). Un pago con tarjeta, transferencia u otro "
            "método distinto de efectivo no puede generar cambio."
        )
