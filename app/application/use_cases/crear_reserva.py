from application.dtos.reservacion_dto import ReservacionDTO
from domain.entities.reservaciones import Reservacion
from domain.entities.tipos_evento import Tipos_Evento
from domain.entities.paquetes_tipos_evento import Paquetes_Tipos_Evento
from domain.entities.pagos_reservacion import Pagos_Reservacion
from domain.ports.reserva_repository import ReservaRepository
from domain.value_objects.horario import Horario

class CrearReservaUseCase:
    def __init__(self, reserva_repository: ReservaRepository):
        self.reserva_repository = reserva_repository

    async def execute(self, reservacion_dto: ReservacionDTO) -> Reservacion:
        # Validar que el tipo de evento exista
        tipo_evento = self.reserva_repository.obtener_tipo_evento(reservacion_dto.tipo_evento_id)
        if not tipo_evento:
            raise ValueError("El tipo de evento no existe.")
        
        # Validar que el paquete sea compatible con el tipo de evento
        paquete_tipo_evento = self.reserva_repository.obtener_paquete_tipo_evento(reservacion_dto.paquete_id, reservacion_dto.tipo_evento_id)
        if not paquete_tipo_evento:
            raise ValueError("El paquete no es compatible con el tipo de evento.")
        
        # Crear la reservación
        reservacion = Reservacion(
            sucursal_id=reservacion_dto.sucursal_id,
            tipo_evento_id=reservacion_dto.tipo_evento_id,
            paquete_id=reservacion_dto.paquete_id,
            nombres_cliente=reservacion_dto.nombres_cliente,
            apellidos_cliente=reservacion_dto.apellidos_cliente,
            telefono_cliente=reservacion_dto.telefono_cliente,
            correo_cliente=reservacion_dto.correo_cliente,
            notas_adicionales=reservacion_dto.notas_adicionales,
            nombre_festejado=reservacion_dto.nombre_festejado,
            edad_festejado=reservacion_dto.edad_festejado,  
            fecha_evento=reservacion_dto.fecha_evento,
            hora_inicio=Horario(reservacion_dto.hora_inicio),
            hora_fin=Horario(reservacion_dto.hora_fin),
            numero_invitados=reservacion_dto.numero_invitados,
            precio_base=reservacion_dto.precio_base,
            precio_personas_extra=reservacion_dto.precio_personas_extra,
            precio_servicio_adicional=reservacion_dto.precio_servicio_adicional,
            precio_total=reservacion_dto.precio_total,
            anticipo=reservacion_dto.anticipo,
            saldo_restante=reservacion_dto.saldo_restante,
            creado_por=reservacion_dto.creado_por
        )

        # Guardar la reservación en el repositorio
        await self.reserva_repository.crear_reserva(reservacion)
        return ReservaOutputDTO(
            id=reservacion.id,
            sucursal_id=reservacion.sucursal_id,
            cliente_id=reservacion.cliente_id,
            tipo_evento_id=reservacion.tipo_evento_id,
            paquete_id=reservacion.paquete_id,
            fecha_evento=reservacion.fecha_evento,
            hora_inicio=reservacion.hora_inicio.hora,
            hora_fin=reservacion.hora_fin.hora,
            invitados=reservacion.numero_invitados,
            notas_adicionales=reservacion.notas_adicionales,
            nombre_festejado=reservacion.nombre_festejado,
            edad_festejado=reservacion.edad_festejado,
            precio_base=reservacion.precio_base,
            precio_personas_extra=reservacion.precio_personas_extra,
            precio_servicio_adicional=reservacion.precio_servicio_adicional,
            precio_total=reservacion.precio_total,
            anticipo=reservacion.anticipo,
            saldo_restante=reservacion.saldo_restante,
            estatus=reservacion.estatus,
            activo=reservacion.activo
        )