from datastclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass
class CrearReservaDTO:
    """
    Clase que representa los datos necesarios para crear una nueva reserva en el sistema de reservas.
    """
    sucursal_id: UUID
    cliente_id: UUID
    tipo_evento_id: UUID
    paquete_id: UUID
    fecha_evento: datetime
    hora_inicio: datetime
    hora_fin: datetime
    invitados: int
    notas_adicionales: str
    nombre_festejado: str
    edad_festejado: int
    precio_base: float
    precio_personas_extra: float
    precio_servicio_adicional: float
    precio_total: float
    anticipo: float
    saldo_restante: float
    creado_por: str

@dataclass
class ActualizarReservaDTO:
    """
    Clase que representa los datos necesarios para actualizar una reserva existente en el sistema de reservas.
    """
    id: UUID
    sucursal_id: UUID
    cliente_id: UUID
    tipo_evento_id: UUID
    paquete_id: UUID
    fecha_evento: datetime
    hora_inicio: datetime
    hora_fin: datetime
    invitados: int
    notas_adicionales: str
    nombre_festejado: str
    edad_festejado: int
    precio_base: float
    precio_personas_extra: float
    precio_servicio_adicional: float
    precio_total: float
    anticipo: float
    saldo_restante: float
    estatus: str
    modificado_por: str

@dataclass
class DetallesReservaDTO:
    """
    Clase que representa los detalles de una reserva en el sistema de reservas.
    """
    id: UUID
    sucursal_id: UUID
    cliente_id: UUID
    tipo_evento_id: UUID
    paquete_id: UUID
    fecha_evento: datetime
    hora_inicio: datetime
    hora_fin: datetime
    invitados: int
    notas_adicionales: str
    nombre_festejado: str
    edad_festejado: int
    precio_base: float
    precio_personas_extra: float
    precio_servicio_adicional: float
    precio_total: float
    anticipo: float
    saldo_restante: float
    estatus: str
    activo: bool
    creado: datetime
    creado_por: str
    modificado: datetime
    modificado_por: str

@dataclass
class ListarReservasDTO:
    """
    Clase que representa los datos necesarios para listar las reservas en el sistema de reservas.
    """
    id: UUID
    sucursal_id: UUID
    cliente_id: UUID
    tipo_evento_id: UUID
    paquete_id: UUID
    fecha_evento: datetime
    hora_inicio: datetime
    hora_fin: datetime
    invitados: int
    notas_adicionales: str
    nombre_festejado: str
    edad_festejado: int
    precio_base: float
    precio_personas_extra: float
    precio_servicio_adicional: float
    precio_total: float
    anticipo: float
    saldo_restante: float
    estatus: str
    activo: bool
    creado: datetime
    creado_por: str
    modificado: datetime
    modificado_por: str

@dataclass
class EliminarReservaDTO:
    """
    Clase que representa los datos necesarios para eliminar una reserva en el sistema de reservas.
    """
    id: UUID
    modificado_por: str

@dataclass
class ReservaOutputDTO:
    """
    Clase que representa los datos de salida de una reserva en el sistema de reservas.
    """
    id: UUID
    sucursal_id: UUID
    cliente_id: UUID
    tipo_evento_id: UUID
    paquete_id: UUID
    fecha_evento: datetime
    hora_inicio: datetime
    hora_fin: datetime
    invitados: int
    notas_adicionales: str
    nombre_festejado: str
    edad_festejado: int
    precio_base: float
    precio_personas_extra: float
    precio_servicio_adicional: float
    precio_total: float
    anticipo: float
    saldo_restante: float
    estatus: str
    activo: bool
    
    