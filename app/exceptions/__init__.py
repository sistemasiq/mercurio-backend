from fastapi import HTTPException, status


class CredencialesInvalidas(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Credenciales incorrectas."},
        )


class NoEncontrado(HTTPException):
    def __init__(self, recurso: str = "Recurso"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"{recurso} no encontrado."},
        )
