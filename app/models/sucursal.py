from uuid import uuid4

from sqlalchemy import text, Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.db.database import Base


class SucursalModel(Base):
    """Sucursal o sede donde se realizan los eventos."""

    __tablename__ = "sucursales"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    nombre = Column(String(150), nullable=False)
    direccion = Column(Text, nullable=True)
    telefono = Column(String(10), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    creado = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    creado_por = Column(PGUUID(as_uuid=True), nullable=True)
    modificado = Column(DateTime(timezone=True), nullable=True, server_default=text("now()"))
    modificado_por = Column(PGUUID(as_uuid=True), nullable=True)

    paquetes = relationship("PaqueteModel", back_populates="sucursal")
    extras = relationship("ExtrasModel", back_populates="sucursal")
    reservaciones = relationship("ReservacionModel", back_populates="sucursal")
