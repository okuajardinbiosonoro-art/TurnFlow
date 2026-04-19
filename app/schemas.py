from datetime import date, time, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, ConfigDict


# ------- SLOT (TURNO) -------

class SlotBase(BaseModel):
    fecha: date
    hora_inicio: time
    hora_fin: time
    capacidad_nominal: int = 30
    capacidad_maxima: int = 30
    estado: str = "abierto"


class SlotCreate(SlotBase):
    pass


class SlotRead(SlotBase):
    id: int
    # Ocupación del turno (se llenará desde la lógica, no desde la BD directamente)
    personas_programadas: int

    # Equivalente a orm_mode = True en Pydantic v1
    model_config = ConfigDict(from_attributes=True)


# ------- BOOKING (GRUPO) -------

class BookingBase(BaseModel):
    slot_id: int
    num_personas: int
    num_manillas: int = 0
    nombre_referencia: Optional[str] = None
    contacto_email: Optional[EmailStr] = None
    contacto_telefono: Optional[str] = None
    estado: str = "programado"
    observacion: str = "N/A"


class BookingCreate(BookingBase):
    pass


class BookingRead(BookingBase):
    id: int
    timestamp_creacion: datetime
    timestamp_ultima_modificacion: datetime

    # También necesita poder leer desde ORM
    model_config = ConfigDict(from_attributes=True)

# ------- RESPUESTAS ENRIQUECIDAS PARA BOOKINGS -------

class BookingWithMeta(BookingRead):
    """
    Booking + información del slot y advertencias de capacidad.
    """
    personas_programadas_slot: int
    capacidad_nominal_slot: int
    capacidad_maxima_slot: int
    warning: Optional[str] = None


class BookingMoveRequest(BaseModel):
    """
    Petición para mover un booking a otro slot.
    """
    nuevo_slot_id: int
    force: bool = False  # permitir exceder capacidad_maxima si es muy necesario


class BookingStatusUpdate(BaseModel):
    """
    Petición para actualizar el estado de un booking.
    """
    estado: str  # programado, check_in, no_show, cancelado

# ------- USUARIOS Y AUTENTICACIÓN -------

class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    password: str
    is_admin: bool = False


class UserRead(UserBase):
    id: int
    is_active: bool
    is_admin: bool

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None

# ------- REPORTES DIARIOS -------

class DailySlotStats(BaseModel):
    fecha: date
    slot_id: int
    hora_inicio: time
    hora_fin: time
    capacidad_nominal: int
    capacidad_maxima: int
    personas_programadas: int
    asistentes: int
    no_show: int
    manillas_programadas: int
    ocupacion_programada: float  # personas_programadas / capacidad_nominal
    ocupacion_real: float        # asistentes / capacidad_nominal


class DailyReportResponse(BaseModel):
    fecha: date
    total_personas_programadas: int
    total_asistentes: int
    total_no_show: int
    total_manillas_programadas: int
    num_slots: int
    csv_path: str  # ruta donde se guardó el archivo en el PC-servidor
    slots: List[DailySlotStats]

# ------- UTILIDADES -------

class InitDayResponse(BaseModel):
    fecha: date
    slots_creados: int
    slots_existentes: int
    total_slots: int


class HealthCheck(BaseModel):
    status: str
    detail: str
