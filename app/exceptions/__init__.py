from fastapi import HTTPException, status


class CredencialesInvalidas(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Credenciales incorrectas."},
        )


class NoEncontrado(HTTPException):
    def __init__(self, recurso: str = "Recurso") -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"{recurso} no encontrado."},
        )


class Conflicto(HTTPException):
    def __init__(self, mensaje: str = "El registro ya existe.") -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": mensaje},
        )


class DatosInvalidos(HTTPException):
    def __init__(self, mensaje: str = "Los datos enviados no son válidos.") -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_DATA", "message": mensaje},
        )


class StockInsuficienteError(HTTPException):
    def __init__(self, insumo_nombre: str, contexto: str = "completar la operación") -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "STOCK_INSUFICIENTE",
                "message": f"No hay stock suficiente de «{insumo_nombre}» para {contexto}.",
            },
        )


class SaldoInsuficienteError(HTTPException):
    def __init__(self, saldo_disponible: int, contexto: str = "realizar el canje") -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "SALDO_INSUFICIENTE",
                "message": (
                    f"Saldo de puntos insuficiente (disponible: {saldo_disponible}) "
                    f"para {contexto}."
                ),
            },
        )
