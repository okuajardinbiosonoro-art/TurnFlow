from datetime import date, time, datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Time,
    DateTime,
    ForeignKey,
    Boolean,
)
from sqlalchemy.orm import relationship

from .database import Base


class Slot(Base):
    """
    Turno de 15 minutos.
    Un día típico tendrá 26 slots (saltando almuerzo).
    """
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, index=True, nullable=False)
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)

    capacidad_nominal = Column(Integer, nullable=False, default=30)
    capacidad_maxima = Column(Integer, nullable=False, default=30)

    estado = Column(String, nullable=False, default="abierto")  # abierto, cerrado, almuerzo…

    # Relación con Bookings (grupos)
    bookings = relationship("Booking", back_populates="slot", cascade="all, delete-orphan")


class Booking(Base):
    """
    Grupo de personas asignadas a un Slot.
    """
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)

    slot_id = Column(Integer, ForeignKey("slots.id"), nullable=False)

    num_personas = Column(Integer, nullable=False)

    num_manillas = Column(Integer, nullable=False, default=0)

    nombre_referencia = Column(String, nullable=True)  # "Familia Gómez", "Colegio X", etc.
    contacto_email = Column(String, nullable=True)
    contacto_telefono = Column(String, nullable=True)

    estado = Column(
        String,
        nullable=False,
        default="programado",
    )  # programado, check_in, no_show, cancelado

    observacion = Column(String, nullable=False, default="N/A")

    timestamp_creacion = Column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    timestamp_ultima_modificacion = Column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relación inversa al Slot
    slot = relationship("Slot", back_populates="bookings")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)