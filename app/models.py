from uuid import uuid4

from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, Numeric, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.database import Base


class SucursalModel(Base):
    __tablename__ = "sucursales"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    nombre = Column(String(150), nullable=False)
    direccion = Column(Text, nullable=True)
    telefono = Column(String(10), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    creado = Column(String, nullable=False)
    creado_por = Column(PGUUID(as_uuid=True), nullable=True)
    modificado = Column(String, nullable=True)
    modificado_por = Column(PGUUID(as_uuid=True), nullable=True)

    paquetes = relationship("PaqueteModel", back_populates="sucursal")
    extras = relationship("ExtrasModel", back_populates="sucursal")
    reservaciones = relationship("ReservacionModel", back_populates="sucursal")


class TipoEventoModel(Base):
    __tablename__ = "tipos_evento"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    nombre = Column(String(100), nullable=False, unique=True)
    descripcion = Column(Text, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    creado = Column(String, nullable=False)
    creado_por = Column(PGUUID(as_uuid=True), nullable=True)
    modificado = Column(String, nullable=True)
    modificado_por = Column(PGUUID(as_uuid=True), nullable=True)

    reservaciones = relationship("ReservacionModel", back_populates="tipo_evento")
    paquete_tipos_evento = relationship("PaqueteTipoEventoModel", back_populates="tipo_evento")


class MetodosPagoModel(Base):
    __tablename__ = "metodos_pago"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    nombre = Column(String(100), nullable=False, unique=True)
    descripcion = Column(Text, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    creado = Column(String, nullable=False)
    creado_por = Column(PGUUID(as_uuid=True), nullable=True)
    modificado = Column(String, nullable=True)
    modificado_por = Column(PGUUID(as_uuid=True), nullable=True)

    pagos_reservaciones = relationship("PagosReservacionModel", back_populates="metodo_pago")


class PaqueteModel(Base):
    __tablename__ = "paquetes"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    sucursal_id = Column(PGUUID(as_uuid=True), ForeignKey("sucursales.id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    duracion_minutos = Column(Integer, nullable=False, default=120)
    personas_incluidas = Column(Integer, nullable=False, default=10)
    precio_base = Column(Numeric(10, 2), nullable=False)
    precio_persona_extra = Column(Numeric(10, 2), nullable=False, default=0)
    activo = Column(Boolean, nullable=False, default=True)
    creado = Column(String, nullable=False)
    creado_por = Column(PGUUID(as_uuid=True), nullable=True)
    modificado = Column(String, nullable=True)
    modificado_por = Column(PGUUID(as_uuid=True), nullable=True)

    sucursal = relationship("SucursalModel", back_populates="paquetes")
    paquete_tipos_evento = relationship("PaqueteTipoEventoModel", back_populates="paquete")
    reservaciones = relationship("ReservacionModel", back_populates="paquete")


class PaqueteTipoEventoModel(Base):
    __tablename__ = "paquete_tipos_evento"

    paquete_id = Column(PGUUID(as_uuid=True), ForeignKey("paquetes.id", ondelete="CASCADE"), primary_key=True)
    tipo_evento_id = Column(PGUUID(as_uuid=True), ForeignKey("tipos_evento.id", ondelete="CASCADE"), primary_key=True)

    paquete = relationship("PaqueteModel", back_populates="paquete_tipos_evento")
    tipo_evento = relationship("TipoEventoModel", back_populates="paquete_tipos_evento")


class ExtrasModel(Base):
    __tablename__ = "extras"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    sucursal_id = Column(PGUUID(as_uuid=True), ForeignKey("sucursales.id", ondelete="CASCADE"), nullable=True)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    precio = Column(Numeric(10, 2), nullable=False)
    unidad = Column(String(20), nullable=False, default="evento")
    activo = Column(Boolean, nullable=False, default=True)
    creado = Column(String, nullable=False)
    creado_por = Column(PGUUID(as_uuid=True), nullable=True)
    modificado = Column(String, nullable=True)
    modificado_por = Column(PGUUID(as_uuid=True), nullable=True)

    sucursal = relationship("SucursalModel", back_populates="extras")
    reservacion_extras = relationship("ReservacionExtrasModel", back_populates="extra")


class ReservacionModel(Base):
    __tablename__ = "reservaciones"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    sucursal_id = Column(PGUUID(as_uuid=True), ForeignKey("sucursales.id", ondelete="RESTRICT"), nullable=False)
    tipo_evento_id = Column(PGUUID(as_uuid=True), ForeignKey("tipos_evento.id", ondelete="RESTRICT"), nullable=False)
    paquete_id = Column(PGUUID(as_uuid=True), ForeignKey("paquetes.id", ondelete="RESTRICT"), nullable=False)

    nombre_cliente = Column(String(150), nullable=False)
    apellidos_cliente = Column(String(150), nullable=True)
    telefono_cliente = Column(String(10), nullable=False)
    email_cliente = Column(String(150), nullable=True)
    notas_cliente = Column(Text, nullable=True)

    nombre_festejado = Column(String(150), nullable=True)
    edad_festejado = Column(Integer, nullable=True)

    fecha_evento = Column(Date, nullable=False)
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)
    numero_personas = Column(Integer, nullable=False)

    precio_base = Column(Numeric(10, 2), nullable=False)
    precio_personas_extra = Column(Numeric(10, 2), nullable=False, default=0)
    precio_extras = Column(Numeric(10, 2), nullable=False, default=0)
    descuento = Column(Numeric(10, 2), nullable=False, default=0)
    precio_total = Column(Numeric(10, 2), nullable=False)
    anticipo = Column(Numeric(10, 2), nullable=False, default=0)

    estado = Column(String(20), nullable=False, default="pendiente")
    notas = Column(Text, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)

    creado = Column(String, nullable=False)
    creado_por = Column(PGUUID(as_uuid=True), nullable=True)
    modificado = Column(String, nullable=True)
    modificado_por = Column(PGUUID(as_uuid=True), nullable=True)

    sucursal = relationship("SucursalModel", back_populates="reservaciones")
    tipo_evento = relationship("TipoEventoModel", back_populates="reservaciones")
    paquete = relationship("PaqueteModel", back_populates="reservaciones")
    extras = relationship("ReservacionExtrasModel", back_populates="reservacion")
    pagos = relationship("PagosReservacionModel", back_populates="reservacion")


class ReservacionExtrasModel(Base):
    __tablename__ = "reservacion_extras"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    reservacion_id = Column(PGUUID(as_uuid=True), ForeignKey("reservaciones.id", ondelete="CASCADE"), nullable=False)
    extra_id = Column(PGUUID(as_uuid=True), ForeignKey("extras.id", ondelete="RESTRICT"), nullable=False)
    cantidad = Column(Integer, nullable=False, default=1)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    creado = Column(String, nullable=False)
    creado_por = Column(PGUUID(as_uuid=True), nullable=True)

    reservacion = relationship("ReservacionModel", back_populates="extras")
    extra = relationship("ExtrasModel", back_populates="reservacion_extras")


class PagosReservacionModel(Base):
    __tablename__ = "pagos_reservacion"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    reservacion_id = Column(PGUUID(as_uuid=True), ForeignKey("reservaciones.id", ondelete="CASCADE"), nullable=False)
    metodo_pago_id = Column(PGUUID(as_uuid=True), ForeignKey("metodos_pago.id", ondelete="RESTRICT"), nullable=False)
    monto = Column(Numeric(10, 2), nullable=False)
    fecha_pago = Column(String, nullable=False)
    notas = Column(Text, nullable=True)
    creado_por = Column(PGUUID(as_uuid=True), nullable=True)

    reservacion = relationship("ReservacionModel", back_populates="pagos")
    metodo_pago = relationship("MetodosPagoModel", back_populates="pagos_reservaciones")
