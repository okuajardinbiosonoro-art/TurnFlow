from datetime import date, time, datetime, timedelta
from typing import List, Tuple, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from . import models


# ---------------- UTILIDADES INTERNAS ---------------- #

def _generar_horarios_slots(fecha: date) -> List[Tuple[time, time]]:
    """
    Genera la lista de (hora_inicio, hora_fin) para los turnos de un día:
    - Desde 09:00 hasta 16:00 (último inicio 16:00)
    - Intervalos de 15 minutos
    - Se saltan 12:00 y 12:15 (almuerzo)
    """
    horarios = []

    inicio_dia = datetime.combine(fecha, time(9, 0))
    ultimo_inicio = datetime.combine(fecha, time(16, 0))
    paso = timedelta(minutes=15)

    almuerzo_inicios = {time(12, 0), time(12, 15)}

    current = inicio_dia
    while current <= ultimo_inicio:
        h_inicio = current.time()
        if h_inicio not in almuerzo_inicios:
            h_fin = (current + paso).time()
            horarios.append((h_inicio, h_fin))
        current += paso

    return horarios


# ---------------- SLOTS (TURNOS) ---------------- #

def get_slots_by_date(db: Session, fecha: date) -> List[models.Slot]:
    return (
        db.query(models.Slot)
        .filter(models.Slot.fecha == fecha)
        .order_by(models.Slot.hora_inicio)
        .all()
    )


def init_slots_for_date(
    db: Session,
    fecha: date,
    capacidad_nominal: int = 30,
    capacidad_maxima: int = 30,
) -> Tuple[int, int]:
    """
    Crea los slots para una fecha si aún no existen.
    Devuelve (slots_creados, slots_existentes_previamente).
    """
    existentes = get_slots_by_date(db, fecha)
    slots_existentes = len(existentes)

    if slots_existentes > 0:
        # Ya hay slots; no creamos nuevos, solo devolvemos conteo
        return 0, slots_existentes

    horarios = _generar_horarios_slots(fecha)

    for h_inicio, h_fin in horarios:
        slot = models.Slot(
            fecha=fecha,
            hora_inicio=h_inicio,
            hora_fin=h_fin,
            capacidad_nominal=capacidad_nominal,
            capacidad_maxima=capacidad_maxima,
            estado="abierto",
        )
        db.add(slot)

    db.commit()
    # Recontamos
    nuevos = get_slots_by_date(db, fecha)
    return len(nuevos), 0


def calcular_personas_por_slot(db: Session, slot_id: int) -> int:
    """
    Calcula cuántas personas hay programadas en un slot (bookings no cancelados).
    """
    total = (
        db.query(func.coalesce(func.sum(models.Booking.num_personas), 0))
        .filter(
            models.Booking.slot_id == slot_id,
            models.Booking.estado != "cancelado",
        )
        .scalar()
    )
    return int(total or 0)


# ---------------- UTILIDADES PARA NO_SHOW AUTOMÁTICO ---------------- #

def mark_past_programmed_as_no_show(db: Session, fecha: date) -> int:
    """
    Marca automáticamente como 'no_show' todos los bookings en estado 'programado'
    cuyo turno (slot) ya haya terminado.

    Reglas:
    - Si fecha < hoy: todos los bookings 'programado' de esa fecha pasan a 'no_show'.
    - Si fecha == hoy: sólo los bookings 'programado' de slots con hora_fin <= ahora.
    - Si fecha > hoy: no hace nada.
    Devuelve la cantidad de bookings actualizados.
    """
    now = datetime.now()
    today = now.date()

    # Fecha futura: nada que hacer
    if fecha > today:
        return 0

    q = (
        db.query(models.Booking)
        .join(models.Slot, models.Booking.slot_id == models.Slot.id)
        .filter(models.Slot.fecha == fecha)
        .filter(models.Booking.estado == "programado")
    )

    if fecha == today:
        # Solo turnos que ya terminaron (hora_fin <= ahora)
        q = q.filter(models.Slot.hora_fin <= now.time())

    bookings_a_actualizar = q.all()
    if not bookings_a_actualizar:
        return 0

    for b in bookings_a_actualizar:
        b.estado = "no_show"
        b.timestamp_ultima_modificacion = datetime.utcnow()

    db.commit()
    return len(bookings_a_actualizar)

# ---------------- USUARIOS ---------------- #

def get_user_by_username(db: Session, username: str) -> models.User | None:
    return db.query(models.User).filter(models.User.username == username).first()


def get_users(db: Session) -> list[models.User]:
    return db.query(models.User).order_by(models.User.username).all()


def create_user(
    db: Session,
    username: str,
    hashed_password: str,
    is_admin: bool = False,
) -> models.User:
    user = models.User(
        username=username,
        hashed_password=hashed_password,
        is_admin=is_admin,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# ---------------- BOOKING (GRUPOS) ---------------- #

def get_slot(db: Session, slot_id: int) -> models.Slot | None:
    return db.query(models.Slot).filter(models.Slot.id == slot_id).first()


def get_booking(db: Session, booking_id: int) -> models.Booking | None:
    return db.query(models.Booking).filter(models.Booking.id == booking_id).first()


def create_booking(
    db: Session,
    slot: models.Slot,
    num_personas: int,
    nombre_referencia: str | None = None,
    contacto_email: str | None = None,
    contacto_telefono: str | None = None,
    observacion: str = "N/A",
    estado: str = "programado",
    num_manillas: int = 0,
) -> models.Booking:
    """
    Crea un booking en un slot ya cargado.
    La lógica de capacidad (warnings, etc.) se maneja fuera para poder
    decidir si se permite o no.
    """
    now = datetime.utcnow()

    booking = models.Booking(
        slot_id=slot.id,
        num_personas=num_personas,
        num_manillas=num_manillas,
        nombre_referencia=nombre_referencia,
        contacto_email=contacto_email,
        contacto_telefono=contacto_telefono,
        observacion=observacion,
        estado=estado,
        timestamp_creacion=now,
        timestamp_ultima_modificacion=now,
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def move_booking(
    db: Session,
    booking: models.Booking,
    nuevo_slot: models.Slot,
) -> models.Booking:
    """
    Mueve un booking de su slot actual a otro.

    Reglas:
    - Actualiza el slot.
    - Resetea el estado a 'programado' (reprogramado).
    - Actualiza timestamp_ultima_modificacion.
    La validación de capacidad se hace fuera.
    """
    booking.slot_id = nuevo_slot.id
    booking.estado = "programado"  # << importante: siempre vuelve a programado
    booking.timestamp_ultima_modificacion = datetime.utcnow()
    db.commit()
    db.refresh(booking)
    return booking



def update_booking_status(
    db: Session,
    booking: models.Booking,
    nuevo_estado: str,
) -> models.Booking:
    """
    Actualiza el estado de un booking (programado, check_in, no_show, cancelado).
    """
    booking.estado = nuevo_estado
    booking.timestamp_ultima_modificacion = datetime.utcnow()
    db.commit()
    db.refresh(booking)
    return booking


def get_bookings_by_slot(db: Session, slot_id: int) -> list[models.Booking]:
    return (
        db.query(models.Booking)
        .filter(models.Booking.slot_id == slot_id)
        .order_by(models.Booking.timestamp_creacion)
        .all()
    )


def get_bookings_by_date(db: Session, fecha: date) -> list[models.Booking]:
    """
    Devuelve todos los bookings de una fecha (cualquier slot de ese día).
    """
    return (
        db.query(models.Booking)
        .join(models.Slot, models.Booking.slot_id == models.Slot.id)
        .filter(models.Slot.fecha == fecha)
        .order_by(models.Slot.hora_inicio, models.Booking.timestamp_creacion)
        .all()
    )


# ---------------- REPORTES / ESTADÍSTICAS ---------------- #

def get_daily_slot_stats(db: Session, fecha: date) -> List[Dict[str, Any]]:
    """
    Calcula estadísticas por slot para una fecha dada.

    Devuelve una lista de dicts con:
    - fecha
    - slot_id
    - hora_inicio, hora_fin
    - capacidad_nominal, capacidad_maxima
    - personas_programadas (no cancelados)
    - asistentes (estado == 'check_in')
    - no_show (estado == 'no_show')
    - ocupacion_programada (personas_programadas / capacidad_nominal)
    - ocupacion_real (asistentes / capacidad_nominal)
    """
    slots = get_slots_by_date(db, fecha)
    stats_list: List[Dict[str, Any]] = []

    for slot in slots:
        bookings = (
            db.query(models.Booking)
            .filter(models.Booking.slot_id == slot.id)
            .all()
        )

        personas_programadas = sum(
            b.num_personas for b in bookings if b.estado != "cancelado"
        )
        asistentes = sum(
            b.num_personas for b in bookings if b.estado == "check_in"
        )
        no_show = sum(
            b.num_personas for b in bookings if b.estado == "no_show"
        )

        manillas_programadas = sum(
            b.num_manillas for b in bookings if b.estado != "cancelado"
        )

        if slot.capacidad_nominal > 0:
            ocup_prog = personas_programadas / slot.capacidad_nominal
            ocup_real = asistentes / slot.capacidad_nominal
        else:
            ocup_prog = 0.0
            ocup_real = 0.0

        stats_list.append(
            {
                "fecha": slot.fecha,
                "slot_id": slot.id,
                "hora_inicio": slot.hora_inicio,
                "hora_fin": slot.hora_fin,
                "capacidad_nominal": slot.capacidad_nominal,
                "capacidad_maxima": slot.capacidad_maxima,
                "personas_programadas": personas_programadas,
                "asistentes": asistentes,
                "no_show": no_show,
                "manillas_programadas": manillas_programadas,
                "ocupacion_programada": ocup_prog,
                "ocupacion_real": ocup_real,
            }
        )

    return stats_list