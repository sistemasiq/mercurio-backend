from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4, uuid4
from domain.value_objects.horario import Horario
from domain.exceptions.reservaciones import CapacidadExcedidaException, HorarioNoDisponibleException, ReservacionNoEncontradaException, ReservacionYaCanceladaException, ReservacionYaConfirmadaException, ReservacionYaFinalizadaException, ReservacionYaPendienteException,   ReservacionYaReprogramadaException, ReservacionYaCanceladaException, ReservacionYaConfirmadaException, ReservacionYaFinalizadaError

@dataclass
class Reservacion:
    """Clase que representa una reservación en el sistema de reservas.
    """
    id: UUID = field(default_factory=uuid4)
    sucursal_id: UUID
    tipo_evento_id: UUID
    paquete_id: UUID
    nombres_cliente: str
    apellidos_cliente: str
    telefono_cliente: str
    correo_cliente: str
    notas_adicionales: str
    nombre_festejado: str
    edad_festejado: int
    fecha_evento: datetime
    hora_inicio: Horario
    hora_fin: Horario
    numero_invitados: int
    precio_base: float
    precio_personas_extra: float
    precio_servicio_adicional: float
    precio_total: float
    anticipo: float
    saldo_restante: float
    estatus: str = {"Pendiente", "Confirmada"}
    activo: bool = True
    creado: datetime = field(default_factory=datetime.now)
    creado_por: str
    modificado: datetime = field(default_factory=datetime.now)
    modificado_por: str

    def __post_init__(self):
        if self.numero_invitados > 100:
            raise CapacidadExcedidaException("La capacidad máxima es de 100 invitados.")
        if self.hora_inicio >= self.hora_fin:
            raise HorarioNoDisponibleException("La hora de inicio debe ser anterior a la hora de fin.")
        if self.fecha_evento < datetime.now():
            raise ValueError("La fecha del evento no puede ser en el pasado.")
        if self.estatus not in {"Pendiente", "Confirmada", "Cancelada", "Reprogramada", "Finalizada"}:
            raise ValueError("El estatus de la reservación debe ser 'Pendiente', 'Confirmada', 'Cancelada', 'Reprogramada' o 'Finalizada'.")
        if not self.nombres_cliente:
            raise ValueError("El nombre del cliente no puede estar vacío.")
        if not self.apellidos_cliente:  
            raise ValueError("El apellido del cliente no puede estar vacío.")   
        if not self.telefono_cliente:
            raise ValueError("El teléfono del cliente no puede estar vacío.")
        if not self.correo_cliente:
            raise ValueError("El correo del cliente no puede estar vacío.")
        if self.precio_total < 0:
            raise ValueError("El precio total no puede ser negativo.")
        if self.anticipo < 0:
            raise ValueError("El anticipo no puede ser negativo.")
        if self.saldo_restante < 0:
            raise ValueError("El saldo restante no puede ser negativo.")