from fastapi import HTTPException, status


class CredencialesInvalidas(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Credenciales incorrectas."},
        )


class SinPermiso(HTTPException):
    def __init__(self, mensaje: str = "No tienes permiso para realizar esta acción."):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": mensaje},
        )


class NoEncontrado(HTTPException):
    def __init__(self, recurso: str = "Recurso"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"{recurso} no encontrado."},
        )


class Conflicto(HTTPException):
    def __init__(self, mensaje: str = "El registro ya existe."):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": mensaje},
        )
