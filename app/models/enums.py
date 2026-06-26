# app/models/enums.py
import enum

class EstadoComanda(enum.Enum):
    PENDIENTE = 'P'
    EN_PROCESO = 'E'
    LISTO = 'L'
    ENTREGADO = 'T'
    CANCELADO = 'C'

class tipo_producto(enum.Enum):
    ALIMENTO = 'A'
    SERVICIO = 'S'
    BEBIDA = 'B'
    ESTANCIA = 'E'