from uuid import uuid4
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from app.database import Base

class ReservacionesModel(Base):
    __tablename__ = "reservaciones"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    sucursal_id = Column(PG_UUID(as_uuid=True), ForeignKey("sucursales.id"), nullable=False)
    tipo_evento_id = Column(PG_UUID(as_uuid=True), ForeignKey("tipos_evento.id"), nullable=False)
    paquete_id = Column(PG_UUID(as_uuid=True), ForeignKey("paquetes.id"), nullable=False)
    nombre_cliente = Column(String(255), nullable=False)
    apellidos_cliente = Column(String(255), nullable=False)
    telefono_cliente = Column(String(20), nullable=False)
    email_cliente = Column(String(255), nullable=False)
    notas_cliente = Column(String(500), nullable=True)
    nombre_festejado = Column(String(255), nullable=True)
    fecha_evento = Column(DateTime, nullable=False)
    hora_inicio = Column(DateTime, nullable=False)
    hora_fin = Column(DateTime, nullable=False)
    numero_personas = Column(Float, nullable=False)
    precio_base = Column(Float, nullable=False)
    precio_personas_extra = Column(Float, nullable=False)
    precio_extras = Column(Float, nullable=False)
    precio_total = Column(Float, nullable=False)
    anticipo = Column(Float, nullable=False)
    saldo_pendiente = Column(Float, nullable=False)
    estado = Column(String(50), nullable=False)
    notas = Column(String(500), nullable=True)
    activo = Column(Boolean, default=True)
    creado = Column(DateTime, default=datetime.utcnow)
    creado_por = Column(String(255), nullable=False)
    modificado = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    modificado_por = Column(String(255), nullable=False)

    sucursal = relationship("Sucursal", back_populates="reservaciones")
    tipo_evento = relationship("TiposEvento", back_populates="reservaciones")
    paquete = relationship("PaqquetesBase", back_populates="reservaciones")
    reservacion_extras = relationship("ReservacionExtras", back_populates="reservacion")
    pagos_reservacion = relationship("PagosReservacion", back_populates="reservacion")
