from uuid import uuid4

from sqlalchemy import text, DateTime, Boolean, Column, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.db.database import Base


class TipoEventoModel(Base):
    """Catálogo de tipos de evento (cumpleaños, boda, graduación, etc.)."""

    __tablename__ = "tipos_evento"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    nombre = Column(String(100), nullable=False, unique=True)
    descripcion = Column(Text, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    creado = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    creado_por = Column(PGUUID(as_uuid=True), nullable=True)
    modificado = Column(DateTime(timezone=True), nullable=True, server_default=text("now()"))
    modificado_por = Column(PGUUID(as_uuid=True), nullable=True)

    reservaciones = relationship("ReservacionModel", back_populates="tipo_evento")
    paquete_tipos_evento = relationship("PaqueteTipoEventoModel", back_populates="tipo_evento")
