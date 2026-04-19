import os
import csv
import smtplib
import asyncio

from email.message import EmailMessage
from email.utils import make_msgid
from datetime import date, datetime, timedelta
from typing import List

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse

from sqlalchemy.orm import Session

from . import models, schemas, crud, auth
from .database import engine, Base, get_db, SessionLocal
from .settings import (
    CHECK_EMAIL_INTERVAL_SECONDS,
    EMAIL_ENABLED,
    EMAIL_FROM,
    EMAIL_LOGO_PATH,
    EMAIL_PASSWORD,
    EMAIL_SMTP_HOST,
    EMAIL_SMTP_PORT,
    EMAIL_SUBJECT_PREFIX,
    EMAIL_USERNAME,
    REPORTS_DIR,
)

# Crear las tablas en la base de datos (si no existen)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TurnFlow API",
    description="Backend para gestión de turnos de TurnFlow (TF)",
    version="0.1.0",
)

def build_okua_html_email(inner_html: str) -> str:
    """
    Envuelve un contenido HTML interno en una plantilla completa
    con el logo de OKÚA Jardín Biosonoro centrado y estilos básicos.
    El logo usa un placeholder 'CID_LOGO_OKUA' que luego se sustituye
    por el Content-ID real en send_email().
    """
    return f"""
<html>
  <body style="margin:0;padding:0;background-color:#f4f4f4;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
      <tr>
        <td align="center" style="padding:24px 12px;">
          <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0"
                 style="max-width:600px;background-color:#ffffff;border-radius:8px;overflow:hidden;
                        font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
            <tr>
              <td align="center" style="padding:24px;background-color:#0b1f26;">
                <img src="cid:CID_LOGO_OKUA"
                     alt="OKÚA Jardín Biosonoro"
                     style="max-width:220px;height:auto;display:block;margin:0 auto;">
              </td>
            </tr>
            <tr>
              <td style="padding:24px 24px 8px 24px;">
                {inner_html}
              </td>
            </tr>
            <tr>
              <td style="padding:16px 24px 24px 24px;
                         font-size:12px;color:#777777;
                         border-top:1px solid #eeeeee;
                         text-align:center;">
                Este mensaje fue generado automáticamente para recordarte tu turno en
                <strong>OKÚA Jardín Biosonoro</strong>.<br>
                Por favor no respondas directamente a este correo.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def send_email(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
    attach_logo: bool = False,
):
    """
    Envía un correo.

    - text_body: versión en texto plano (para clientes antiguos).
    - html_body: versión HTML profesional (opcional).
    - attach_logo: si es True, intenta adjuntar el logo de OKÚA inline.
    """
    if not EMAIL_ENABLED:
        print(f"[EMAIL DESACTIVADO] A {to_email}: {subject}\n{text_body}\n")
        if html_body:
            print("[EMAIL HTML PREVIEW]\n", html_body)
        return

    if not EMAIL_USERNAME or not EMAIL_PASSWORD:
        raise RuntimeError(
            "EMAIL_ENABLED está activo, pero faltan EMAIL_USERNAME y/o EMAIL_PASSWORD en el entorno."
        )

    msg = EmailMessage()
    msg["From"] = EMAIL_FROM or EMAIL_USERNAME
    msg["To"] = to_email
    msg["Subject"] = subject

    if html_body:
        # Siempre incluimos texto plano como fallback
        msg.set_content(text_body)

        logo_cid = None
        html_to_send = html_body

        if attach_logo:
            # make_msgid devuelve algo como '<abc@dominio>'
            logo_cid = make_msgid(domain="okua.local")
            # En el HTML usamos la versión sin los '<>'
            html_to_send = html_body.replace("CID_LOGO_OKUA", logo_cid[1:-1])

        msg.add_alternative(html_to_send, subtype="html")

        if attach_logo and os.path.exists(EMAIL_LOGO_PATH):
            try:
                with open(EMAIL_LOGO_PATH, "rb") as f:
                    img_data = f.read()

                # Buscamos la parte HTML para adjuntarle el logo como contenido relacionado
                for part in msg.iter_parts():
                    if part.get_content_type() == "text/html":
                        part.add_related(
                            img_data,
                            maintype="image",
                            subtype="png",
                            cid=logo_cid,
                        )
                        break
            except Exception as e:
                print(f"[EMAIL LOGO] No se pudo adjuntar el logo: {e}")
    else:
        # Solo texto plano
        msg.set_content(text_body)

    with smtplib.SMTP_SSL(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT) as server:
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        server.send_message(msg)


@app.post("/notifications/email/test")
def test_email(
    to_email: str,
    current_user: schemas.UserRead = Depends(auth.get_current_active_user),
):
    """
    Envía un correo de prueba con el diseño de OKÚA.
    """
    asunto = f"{EMAIL_SUBJECT_PREFIX}Correo de prueba"

    text_body = (
        "Hola,\n\n"
        "Este es un correo de prueba enviado desde el sistema de turnos de "
        "OKÚA Jardín Biosonoro.\n\n"
        "Si estás leyendo este mensaje, la configuración de correo funciona correctamente.\n\n"
        "Saludos,\n"
        "OKÚA Jardín Biosonoro\n"
    )

    inner_html = """
    <p style="margin:0 0 16px 0;font-size:16px;line-height:1.5;color:#333333;">
      Hola,
    </p>
    <p style="margin:0 0 16px 0;font-size:16px;line-height:1.5;color:#333333;">
      Este es un correo de prueba enviado desde el sistema de turnos de
      <strong>OKÚA Jardín Biosonoro</strong>.
    </p>
    <p style="margin:0 0 16px 0;font-size:14px;line-height:1.6;color:#333333;">
      Si estás leyendo este mensaje, la configuración de correo y el diseño HTML
      están funcionando correctamente.
    </p>
    <p style="margin:0;font-size:14px;line-height:1.6;color:#333333;">
      Muchas gracias por confiar en nosotros.<br>
      <strong>Equipo de OKÚA Jardín Biosonoro</strong>
    </p>
    """

    html_body = build_okua_html_email(inner_html)

    try:
        send_email(to_email, asunto, text_body, html_body=html_body, attach_logo=True)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al enviar correo de prueba: {e}",
        )

    return {"ok": True, "to": to_email}

# Para evitar enviar duplicado mientras el servidor está encendido
notified_email_bookings: set[int] = set()
last_notified_date: date | None = None  # limpiamos el set al cambiar de día

def process_upcoming_email_notifications(db: Session, minutos_ventana: int = 10) -> dict:
    """
    Lógica central para buscar bookings próximos y enviarles correo.
    Se usa tanto desde el endpoint manual como desde el scheduler automático.
    """
    ahora = datetime.now()
    hoy = ahora.date()
    ventana_fin = ahora + timedelta(minutes=minutos_ventana)

    global last_notified_date

    # Si cambiamos de día, limpiamos el set de bookings ya notificados
    if last_notified_date != hoy:
        notified_email_bookings.clear()
        last_notified_date = hoy

    # Obtenemos (Booking, Slot) en una sola consulta
    results = (
        db.query(models.Booking, models.Slot)
        .join(models.Slot, models.Booking.slot_id == models.Slot.id)
        .filter(models.Booking.estado == "programado")
        .filter(models.Booking.contacto_email.isnot(None))
        .filter(models.Slot.fecha == hoy)
        .all()
    )

    enviados = 0
    candidatos = 0

    for booking, slot in results:
        # Evitar duplicados mientras el servidor está levantado
        if booking.id in notified_email_bookings:
            continue

        # Comprobar si cae en la ventana de tiempo
        inicio_dt = datetime.combine(slot.fecha, slot.hora_inicio)
        if not (ahora <= inicio_dt <= ventana_fin):
            continue

        candidatos += 1

        fecha_str = slot.fecha.strftime("%d/%m/%Y")
        hora_str = slot.hora_inicio.strftime("%H:%M")

        asunto = f"{EMAIL_SUBJECT_PREFIX}Recordatorio de su visita ({hora_str})"

        text_body = (
            "Hola,\n\n"
            "Este es un recordatorio de su visita a OKÚA Jardín Biosonoro.\n\n"
            f"Fecha del turno: {fecha_str}\n"
            f"Hora de inicio: {hora_str}\n"
            f"Número de personas en el grupo: {booking.num_personas}\n\n"
            "Importante: En caso de no presentarse en su turno correspondiente, "
            "le será asignado uno nuevo según la disponibilidad del sistema. "
            "Si no se cuenta con disponibilidad o no puede tomar otro turno, "
            "NO se realizará el reembolso del dinero.\n\n"
            "Por tal motivo, los invitamos a ser puntuales y evitar contratiempos; "
            "de esta manera podremos garantizarles una experiencia maravillosa. "
            "Muchas gracias por su comprensión.\n\n"
            "OKÚA Jardín Biosonoro\n"
        )


        # Versión HTML dentro de nuestra plantilla
        inner_html = f"""
        <p style="margin:0 0 16px 0;font-size:16px;line-height:1.5;color:#333333;">
          Hola,
        </p>
        <p style="margin:0 0 16px 0;font-size:16px;line-height:1.5;color:#333333;">
          Este es un recordatorio de su visita a
          <strong>OKÚA Jardín Biosonoro</strong>.
        </p>
        <table role="presentation" cellspacing="0" cellpadding="0" border="0"
               style="width:100%;margin:0 0 16px 0;font-size:14px;color:#333333;">
          <tr>
            <td style="padding:4px 0;width:40%;font-weight:600;">Fecha del turno:</td>
            <td style="padding:4px 0;">{fecha_str}</td>
          </tr>
          <tr>
            <td style="padding:4px 0;width:40%;font-weight:600;">Hora de inicio:</td>
            <td style="padding:4px 0;">{hora_str}</td>
          </tr>
          <tr>
            <td style="padding:4px 0;width:40%;font-weight:600;">Personas en el grupo:</td>
            <td style="padding:4px 0;">{booking.num_personas}</td>
          </tr>
        </table>
        <p style="margin:0 0 12px 0;font-size:14px;line-height:1.6;color:#333333;">
          <strong>Importante:</strong> En caso de no presentarse en su turno correspondiente,
          le será asignado uno nuevo según la disponibilidad del sistema. Si no se cuenta con
          disponibilidad o no puede tomar otro turno, <strong>NO se realizará el reembolso del dinero.</strong>
        </p>
        <p style="margin:0 0 16px 0;font-size:14px;line-height:1.6;color:#333333;">
          Por tal motivo, los invitamos a ser puntuales y evitar contratiempos; de esta manera
          podremos garantizarles una experiencia maravillosa. Muchas gracias por su comprensión.
        </p>
        <p style="margin:0;font-size:14px;line-height:1.6;color:#333333;">
          <strong>Equipo de OKÚA Jardín Biosonoro</strong>
        </p>
        """

        html_body = build_okua_html_email(inner_html)

        try:
            send_email(
                booking.contacto_email,
                asunto,
                text_body,
                html_body=html_body,
                attach_logo=True,
            )
            notified_email_bookings.add(booking.id)
            enviados += 1
        except Exception as e:
            print(f"[ERROR EMAIL] No se pudo enviar a {booking.contacto_email}: {e}")

    return {
        "fecha": hoy.isoformat(),
        "minutos_ventana": minutos_ventana,
        "candidatos": candidatos,
        "enviados": enviados,
    }


@app.post("/notifications/email/upcoming")
def enviar_notificaciones_email_proximas(
    minutos_ventana: int = 10,
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(auth.get_current_active_user),
):
    """
    Endpoint manual para enviar correos a los grupos cuyo turno empieza
    en los próximos `minutos_ventana` minutos. Reutiliza la lógica central.
    """
    return process_upcoming_email_notifications(db=db, minutos_ventana=minutos_ventana)

# Carpeta de archivos estáticos (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ==================== AUTENTICACIÓN / USUARIOS ==================== #

@app.post("/auth/bootstrap-admin", response_model=schemas.UserRead)
def bootstrap_admin(
    user_in: schemas.UserCreate,
    db: Session = Depends(get_db),
):
    """
    Crea el primer usuario administrador.
    Solo se permite si no existe ningún usuario en la base de datos.
    """
    users = crud.get_users(db)
    if users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existen usuarios. Use /auth/users con un admin logueado.",
        )

    # Fuerza is_admin=True para este primer usuario
    hashed_pw = auth.get_password_hash(user_in.password)
    user = crud.create_user(
        db=db,
        username=user_in.username,
        hashed_password=hashed_pw,
        is_admin=True,
    )
    return schemas.UserRead.model_validate(user)


@app.post("/auth/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Login con username + password.

    Devuelve un access_token JWT para usar en Authorization: Bearer <token>.
    """
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth.create_access_token(
        data={"sub": user.username},
    )

    return schemas.Token(access_token=access_token, token_type="bearer")


@app.post("/auth/users", response_model=schemas.UserRead)
def crear_usuario(
    user_in: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_admin: schemas.UserRead = Depends(auth.get_current_admin_user),
):
    """
    Crea un nuevo usuario (operario o admin).
    Solo accesible para un admin logueado.
    """
    existing = crud.get_user_by_username(db, user_in.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con ese username.",
        )

    hashed_pw = auth.get_password_hash(user_in.password)
    user = crud.create_user(
        db=db,
        username=user_in.username,
        hashed_password=hashed_pw,
        is_admin=user_in.is_admin,
    )
    return schemas.UserRead.model_validate(user)


@app.get("/auth/users", response_model=list[schemas.UserRead])
def listar_usuarios(
    db: Session = Depends(get_db),
    current_admin: schemas.UserRead = Depends(auth.get_current_admin_user),
):
    users = crud.get_users(db)
    return [schemas.UserRead.model_validate(u) for u in users]


@app.get("/auth/me", response_model=schemas.UserRead)
def leer_usuario_actual(
    current_user: schemas.UserRead = Depends(auth.get_current_active_user),
):
    return current_user


@app.get("/")
def root():
    # Redirige a la interfaz web
    return RedirectResponse(url="/static/index.html")


@app.get("/health", response_model=schemas.HealthCheck)
def health_check():
    return schemas.HealthCheck(
        status="ok",
        detail="TurnFlow backend funcionando",
    )


@app.post("/days/{fecha_str}/init", response_model=schemas.InitDayResponse)
def init_day_slots(
    fecha_str: str,
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(auth.get_current_active_user),
):
    """
    Inicializa los slots (turnos) de un día específico.

    - Crea los turnos de 15 min entre 09:00 y 16:00
    - Omite 12:00 y 12:15 (almuerzo)
    - Si ya existen slots para esa fecha, no crea nuevos
    """
    try:
        fecha = date.fromisoformat(fecha_str)  # Formato: YYYY-MM-DD
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha inválida, use YYYY-MM-DD")

    slots_creados, slots_existentes = crud.init_slots_for_date(db, fecha)

    total_slots = slots_creados + slots_existentes

    return schemas.InitDayResponse(
        fecha=fecha,
        slots_creados=slots_creados,
        slots_existentes=slots_existentes,
        total_slots=total_slots,
    )


@app.get("/slots/{fecha_str}", response_model=List[schemas.SlotRead])
def listar_slots_por_dia(
    fecha_str: str,
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(auth.get_current_active_user),
):
    """
    Lista todos los slots (turnos) de una fecha con su ocupación actual
    y un estado calculado dinámicamente según la hora local.

    Además, antes de calcular, marca automáticamente como 'no_show'
    todos los bookings 'programado' cuyos turnos ya hayan terminado.
    """
    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha inválida, use YYYY-MM-DD")

    # 🔹 Actualizar automáticamente no_show para turnos ya terminados
    crud.mark_past_programmed_as_no_show(db, fecha)

    slots = crud.get_slots_by_date(db, fecha)

    if not slots:
        return []

    hoy = date.today()
    ahora = datetime.now().time()

    resultado = []
    for slot in slots:
        personas = crud.calcular_personas_por_slot(db, slot.id)

        # Estado dinámico
        if slot.fecha < hoy:
            estado_runtime = "finalizado"
        elif slot.fecha > hoy:
            estado_runtime = "pendiente"
        else:
            # misma fecha
            if ahora < slot.hora_inicio:
                estado_runtime = "pendiente"
            elif ahora >= slot.hora_fin:
                estado_runtime = "finalizado"
            else:
                estado_runtime = "en curso"

        resultado.append(
            schemas.SlotRead(
                id=slot.id,
                fecha=slot.fecha,
                hora_inicio=slot.hora_inicio,
                hora_fin=slot.hora_fin,
                capacidad_nominal=slot.capacidad_nominal,
                capacidad_maxima=slot.capacidad_maxima,
                estado=estado_runtime,
                personas_programadas=personas,
            )
        )

    return resultado


@app.post("/bookings/", response_model=schemas.BookingRead)
def crear_booking(
    booking_in: schemas.BookingCreate,
    force: bool = False,  # se mantiene por compatibilidad, pero NO habilita pasar de 30
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(auth.get_current_active_user),
):
    """
    Crea un nuevo grupo (booking) en un turno dado.

    REGLAS (nuevo requisito):
    - Máximo absoluto por turno: 30 personas.
    - Si el nuevo grupo hace que el turno pase de 30 → error 400 SIEMPRE (aunque force=True).
    """
    # Verificar que el slot existe
    slot = crud.get_slot(db, booking_in.slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot no encontrado")

    # No permitir agregar grupos a turnos ya finalizados
    hoy = date.today()
    ahora = datetime.now().time()
    if slot.fecha < hoy or (slot.fecha == hoy and ahora >= slot.hora_fin):
        raise HTTPException(
            status_code=400,
            detail="No se pueden agregar grupos a un turno que ya finalizó.",
        )

    if booking_in.num_personas <= 0:
        raise HTTPException(status_code=400, detail="num_personas debe ser mayor que cero")
    
    # VALIDACIONES DE MANILLAS
    if booking_in.num_manillas < 0:
        raise HTTPException(status_code=400, detail="num_manillas no puede ser negativo")
    if booking_in.num_manillas > booking_in.num_personas:
        raise HTTPException(
            status_code=400,
            detail="No puede haber más manillas que personas en el grupo.",
        )

    # ------ LÓGICA DE CAPACIDAD DURA (usa capacidad_nominal del slot) ------ #
    personas_actuales = crud.calcular_personas_por_slot(db, booking_in.slot_id)
    nuevo_total = personas_actuales + booking_in.num_personas
    limite = slot.capacidad_nominal  # hoy es 30, y será el máximo absoluto

    if nuevo_total > limite:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No se pueden programar más de {limite} personas en este turno. "
                f"Actualmente hay {personas_actuales} personas programadas y "
                f"el nuevo grupo tiene {booking_in.num_personas}."
            ),
        )
    # ---------------------------------------- #

    # Crear el booking usando tu crud actual (misma firma que ya tenías)
    booking = crud.create_booking(
        db=db,
        slot=slot,
        num_personas=booking_in.num_personas,
        nombre_referencia=booking_in.nombre_referencia,
        contacto_email=booking_in.contacto_email,
        contacto_telefono=booking_in.contacto_telefono,
        observacion=booking_in.observacion,
        estado=booking_in.estado,
        num_manillas=booking_in.num_manillas,
    )

    return schemas.BookingRead.model_validate(booking)


@app.get("/slots/{slot_id}/bookings", response_model=List[schemas.BookingRead])
def listar_bookings_por_slot(
    slot_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(auth.get_current_active_user),
):
    """
    Lista todos los grupos (bookings) asociados a un slot.

    Antes de listar, se actualizan automáticamente como 'no_show'
    los bookings 'programado' de turnos ya finalizados en esa fecha.
    """
    slot = crud.get_slot(db, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot no encontrado")

    # Actualizar no_show para la fecha de este slot
    crud.mark_past_programmed_as_no_show(db, slot.fecha)

    bookings = crud.get_bookings_by_slot(db, slot_id)
    return bookings


@app.put("/bookings/{booking_id}/move", response_model=schemas.BookingRead)
def mover_booking(
    booking_id: int,
    move_req: schemas.BookingMoveRequest,
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(auth.get_current_active_user),
):
    """
    Mueve un grupo (booking) a otro turno.

    REGLAS:
    - No se puede mover a turnos ya finalizados.
    - El turno destino nunca puede quedar con más de 30 personas.
    """
    # 1) Obtener el booking
    booking = crud.get_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking no encontrado")

    # 2) Obtener el nuevo slot
    nuevo_slot = crud.get_slot(db, move_req.nuevo_slot_id)
    if not nuevo_slot:
        raise HTTPException(status_code=404, detail="Nuevo slot no encontrado")

    # Si el turno destino es el mismo, no hacemos nada especial
    if nuevo_slot.id == booking.slot_id:
        return schemas.BookingRead.model_validate(booking)

    # 3) No permitir mover a un turno ya finalizado
    hoy = date.today()
    ahora = datetime.now().time()
    if nuevo_slot.fecha < hoy or (nuevo_slot.fecha == hoy and ahora >= nuevo_slot.hora_fin):
        raise HTTPException(
            status_code=400,
            detail="No se puede mover el grupo a un turno que ya finalizó.",
        )

    # 4) Comprobar capacidad dura de 30 personas en el turno destino
    personas_actuales_destino = crud.calcular_personas_por_slot(db, nuevo_slot.id)
    nuevo_total = personas_actuales_destino + booking.num_personas
    limite = nuevo_slot.capacidad_nominal  # 30

    if nuevo_total > limite:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No se puede mover el grupo a este turno porque se superarían las "
                f"{limite} personas permitidas. "
                f"Actualmente hay {personas_actuales_destino} personas programadas "
                f"y este grupo tiene {booking.num_personas}."
            ),
        )

    # 5) Hacer el movimiento usando la función correcta del CRUD
    booking_actualizado = crud.move_booking(db, booking, nuevo_slot)

    return schemas.BookingRead.model_validate(booking_actualizado)


@app.put("/bookings/{booking_id}/status", response_model=schemas.BookingRead)
def actualizar_estado_booking(
    booking_id: int,
    status_update: schemas.BookingStatusUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(auth.get_current_active_user),
):
    """
    Actualiza el estado de un booking:
    - programado
    - check_in
    - no_show
    - cancelado
    """
    booking = crud.get_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking no encontrado")

    nuevo_estado = status_update.estado
    estados_validos = {"programado", "check_in", "no_show", "cancelado"}
    if nuevo_estado not in estados_validos:
        raise HTTPException(
            status_code=400,
            detail=f"Estado inválido. Debe ser uno de: {', '.join(estados_validos)}",
        )

    booking = crud.update_booking_status(db, booking, nuevo_estado)

    return booking


@app.get("/bookings/day/{fecha_str}", response_model=List[schemas.BookingRead])
def listar_bookings_por_dia(
    fecha_str: str,
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(auth.get_current_active_user),
):
    """
    Lista todos los bookings de una fecha, sin importar el slot.
    Antes de listar, marca automáticamente como 'no_show' todos
    los bookings 'programado' cuyos turnos ya hayan terminado.
    """
    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha inválida, use YYYY-MM-DD")

    # 🔹 Actualizar no_show para esa fecha
    crud.mark_past_programmed_as_no_show(db, fecha)

    bookings = crud.get_bookings_by_date(db, fecha)
    return bookings


@app.post("/reports/daily/{fecha_str}", response_model=schemas.DailyReportResponse)
def generar_reporte_diario_csv(
    fecha_str: str,
    db: Session = Depends(get_db),
    current_user: schemas.UserRead = Depends(auth.get_current_active_user),
):
    """
    Genera un reporte diario en CSV para la fecha indicada.

    - Calcula estadísticas por slot (ocupación, asistentes, no_show).
    - Guarda un archivo CSV en la carpeta ./reports del proyecto.
    - Devuelve un resumen y la ruta del archivo generado.
    """
    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha inválida, use YYYY-MM-DD")

    crud.mark_past_programmed_as_no_show(db, fecha)

    stats_list = crud.get_daily_slot_stats(db, fecha)

    if not stats_list:
        # No hay slots para ese día; probablemente no se ha inicializado
        raise HTTPException(
            status_code=404,
            detail="No hay slots para la fecha indicada. Inicialice el día primero.",
        )

    # Asegurar la carpeta de reportes
    os.makedirs(REPORTS_DIR, exist_ok=True)

    # Nombre de archivo: turnflow_report_YYYY-MM-DD.csv
    filename = f"turnflow_report_{fecha.isoformat()}.csv"
    filepath = os.path.join(REPORTS_DIR, filename)

    # Escribir CSV
    with open(filepath, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile, delimiter=";")

        # Encabezados
        writer.writerow(
            [
                "fecha",
                "slot_id",
                "hora_inicio",
                "hora_fin",
                "capacidad_nominal",
                "capacidad_maxima",
                "personas_programadas",
                "manillas_programadas",
                "asistentes",
                "no_show",
                "ocupacion_programada",  # en porcentaje (0-100)
                "ocupacion_real",        # en porcentaje (0-100)
            ]
        )

        total_programadas = 0
        total_asistentes = 0
        total_no_show = 0
        total_manillas_programadas = 0

        for s in stats_list:
            total_programadas += s["personas_programadas"]
            total_asistentes += s["asistentes"]
            total_no_show += s["no_show"]
            total_manillas_programadas += s.get("manillas_programadas", 0)

            # Convertimos a porcentaje *100 y redondeamos a 2 decimales
            ocup_prog_pct = round(s["ocupacion_programada"] * 100, 2)
            ocup_real_pct = round(s["ocupacion_real"] * 100, 2)

            writer.writerow(
                [
                    s["fecha"].isoformat(),
                    s["slot_id"],
                    s["hora_inicio"].strftime("%H:%M"),
                    s["hora_fin"].strftime("%H:%M"),
                    s["capacidad_nominal"],
                    s["capacidad_maxima"],
                    s["personas_programadas"],
                    s["manillas_programadas"],
                    s["asistentes"],
                    s["no_show"],
                    ocup_prog_pct,
                    ocup_real_pct,
                ]
            )

    # Construir respuesta para la API
    daily_stats_models: list[schemas.DailySlotStats] = []
    for s in stats_list:
        daily_stats_models.append(
            schemas.DailySlotStats(
                fecha=s["fecha"],
                slot_id=s["slot_id"],
                hora_inicio=s["hora_inicio"],
                hora_fin=s["hora_fin"],
                capacidad_nominal=s["capacidad_nominal"],
                capacidad_maxima=s["capacidad_maxima"],
                personas_programadas=s["personas_programadas"],
                asistentes=s["asistentes"],
                no_show=s["no_show"],
                manillas_programadas=s["manillas_programadas"],
                ocupacion_programada=s["ocupacion_programada"],
                ocupacion_real=s["ocupacion_real"],
            )
        )

    return schemas.DailyReportResponse(
        fecha=fecha,
        total_personas_programadas=total_programadas,
        total_asistentes=total_asistentes,
        total_no_show=total_no_show,
        total_manillas_programadas=total_manillas_programadas,
        num_slots=len(stats_list),
        csv_path=filepath,
        slots=daily_stats_models,
    )


@app.get("/reports/daily/{fecha_str}/download")
def descargar_reporte_diario_csv(
    fecha_str: str,
    current_user: schemas.UserRead = Depends(auth.get_current_active_user),
):
    """
    Devuelve el archivo CSV del reporte diario como descarga.

    Si el archivo no existe aún, devuelve 404 (primero hay que generarlo
    con POST /reports/daily/{fecha_str}).
    """
    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha inválida, use YYYY-MM-DD")

    filename = f"turnflow_report_{fecha.isoformat()}.csv"
    filepath = os.path.join(REPORTS_DIR, filename)

    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=404,
            detail="El archivo de reporte no existe. Genérelo primero.",
        )

    return FileResponse(
        path=filepath,
        media_type="text/csv",
        filename=filename,
    )

# ==================== SCHEDULER DE EMAIL AUTOMÁTICO ==================== #


async def email_scheduler_loop():
    """
    Bucle en segundo plano que revisa periódicamente los turnos próximos
    y envía correos automáticos ~10 minutos antes.

    NOTA:
    - Usa la hora local del servidor.
    - Requiere que EMAIL_ENABLED = True y el SMTP esté bien configurado.
    """
    if not EMAIL_ENABLED:
        return

    # Pequeña espera inicial para dar tiempo a que la app arranque del todo
    await asyncio.sleep(5)

    while True:
        db = None
        try:
            db = SessionLocal()
            result = process_upcoming_email_notifications(db, minutos_ventana=10)
            if result.get("enviados", 0) > 0:
                print(
                    f"[EMAIL AUTO] {result['enviados']} correo(s) enviado(s) "
                    f"para hoy {result['fecha']} (ventana {result['minutos_ventana']} min)."
                )
        except Exception as e:
            print(f"[EMAIL AUTO ERROR] {e}")
        finally:
            if db is not None:
                db.close()

        await asyncio.sleep(CHECK_EMAIL_INTERVAL_SECONDS)


@app.on_event("startup")
async def startup_event():
    """
    Evento de inicio de FastAPI.
    Lanza el scheduler de correos automáticos en segundo plano.
    """
    if EMAIL_ENABLED:
        asyncio.create_task(email_scheduler_loop())
