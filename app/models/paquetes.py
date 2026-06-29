from uuid import uuid4

from sqlalchemy import text, DateTime, Boolean, Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.db.database import Base


class PaqueteModel(Base):
    """Paquete de servicio ofrecido por una sucursal para un evento."""

    __tablename__ = "paquetes"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    sucursal_id = Column(PGUUID(as_uuid=True), ForeignKey("sucursales.id"), nullable=False)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    duracion_minutos = Column(Integer, nullable=False, default=120)
    personas_incluidas = Column(Integer, nullable=False, default=10)
    precio_base = Column(Numeric(10, 2), nullable=False)
    precio_persona_extra = Column(Numeric(10, 2), nullable=False, default=0)
    activo = Column(Boolean, nullable=False, default=True)
    creado = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    creado_por = Column(PGUUID(as_uuid=True), nullable=True)
    modificado = Column(DateTime(timezone=True), nullable=True, server_default=text("now()"))
    modificado_por = Column(PGUUID(as_uuid=True), nullable=True)

    sucursal = relationship("SucursalModel", back_populates="paquetes")
    paquete_tipos_evento = relationship("PaqueteTipoEventoModel", back_populates="paquete")
    reservaciones = relationship("ReservacionModel", back_populates="paquete")
