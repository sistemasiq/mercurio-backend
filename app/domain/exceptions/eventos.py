"""Excepciones de dominio del módulo eventos (independientes de FastAPI)."""


class ErrorDominioEventos(Exception):
    """Base de los errores de negocio del módulo eventos."""


class ReservaNoEncontrada(ErrorDominioEventos):
    pass


class ExtraNoEncontrado(ErrorDominioEventos):
    pass


class ExtraInvalido(ErrorDominioEventos):
    pass
