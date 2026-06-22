from uuid import uuid4

from sqlalchemy import text, DateTime, Boolean, Column, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.db.database import Base


class ExtrasModel(Base):
    """Servicios o productos adicionales que se pueden agregar a una reservación."""

    __tablename__ = "extras"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    sucursal_id = Column(PGUUID(as_uuid=True), ForeignKey("sucursales.id"), nullable=True)  # None = extra global
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    precio = Column(Numeric(10, 2), nullable=False)
    unidad = Column(String(50), nullable=False, default="evento")  # evento | persona | hora
    activo = Column(Boolean, nullable=False, default=True)
    creado = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    creado_por = Column(PGUUID(as_uuid=True), nullable=True)
    modificado = Column(DateTime(timezone=True), nullable=True, server_default=text("now()"))
    modificado_por = Column(PGUUID(as_uuid=True), nullable=True)

    sucursal = relationship("SucursalModel", back_populates="extras")
    reservacion_extras = relationship("ReservacionExtrasModel", back_populates="extra")
