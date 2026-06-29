from uuid import uuid4

from sqlalchemy import text, Boolean, Column, Computed, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.db.database import Base


class ReservacionModel(Base):
    """Reservación de un evento en una sucursal."""

    __tablename__ = "reservaciones"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    sucursal_id = Column(PGUUID(as_uuid=True), ForeignKey("sucursales.id"), nullable=False)
    tipo_evento_id = Column(PGUUID(as_uuid=True), ForeignKey("tipos_evento.id"), nullable=False)
    paquete_id = Column(PGUUID(as_uuid=True), ForeignKey("paquetes.id"), nullable=False)

    # Datos del cliente
    nombre_cliente = Column(String(150), nullable=False)
    apellidos_cliente = Column(String(150), nullable=True)
    telefono_cliente = Column(String(10), nullable=False)
    email_cliente = Column(String(150), nullable=True)
    notas_cliente = Column(Text, nullable=True)

    # Datos del festejado
    nombre_festejado = Column(String(150), nullable=True)
    edad_festejado = Column(Integer, nullable=True)

    # Fecha y horario
    fecha_evento = Column(Date, nullable=False)
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)

    # Precios
    numero_personas = Column(Integer, nullable=False)
    precio_base = Column(Numeric(10, 2), nullable=False)
    precio_personas_extra = Column(Numeric(10, 2), nullable=False, default=0)
    precio_extras = Column(Numeric(10, 2), nullable=False, default=0)
    descuento = Column(Numeric(10, 2), nullable=False, default=0)
    precio_total = Column(Numeric(10, 2), nullable=False)
    anticipo = Column(Numeric(10, 2), nullable=False, default=0)
    saldo_pendiente = Column(Numeric(10, 2), Computed("precio_total - anticipo", persisted=True))

    # Estado y notas
    estado = Column(String(20), nullable=False, default="pendiente")
    notas = Column(Text, nullable=True)

    # Auditoría
    activo = Column(Boolean, nullable=False, default=True)
    creado = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    creado_por = Column(PGUUID(as_uuid=True), nullable=True)
    modificado = Column(DateTime(timezone=True), nullable=True, server_default=text("now()"))
    modificado_por = Column(PGUUID(as_uuid=True), nullable=True)

    sucursal = relationship("SucursalModel", back_populates="reservaciones")
    tipo_evento = relationship("TipoEventoModel", back_populates="reservaciones")
    paquete = relationship("PaqueteModel", back_populates="reservaciones")
    reservacion_extras = relationship("ReservacionExtrasModel", back_populates="reservacion")
    pagos = relationship("PagosReservacionModel", back_populates="reservacion")
