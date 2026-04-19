# TurnFlow

TurnFlow es un sistema de gestión de turnos para OKÚA Jardín Biosonoro.
El proyecto combina una API en FastAPI, autenticación JWT y una interfaz web estática servida desde el mismo backend.

## Proposito

Centralizar la operación diaria de turnos, grupos, check-in y reportes CSV sin depender de una infraestructura compleja.

## Stack Tecnologico

- Backend: FastAPI
- ORM y persistencia: SQLAlchemy + SQLite
- Autenticación: JWT con `python-jose` y hash de contraseñas con `passlib[bcrypt]`
- Frontend: HTML, CSS y JavaScript vanilla
- Servidor local: Uvicorn
- Configuracion local: `python-dotenv`

## Requisitos

- Python 3.11 o superior
- `pip`
- Entorno virtual local recomendado (`.venv`)

## Instalacion

```bash
git clone https://github.com/okuajardinbiosonoro-art/TurnFlow.git
cd TurnFlow
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

En Linux o macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Configuracion

1. Copia `.env.example` a `.env`.
2. Completa las variables de entorno reales.
3. No subas `.env` al repositorio.

Variables principales:

| Variable | Proposito | Ejemplo |
| --- | --- | --- |
| `DATABASE_URL` | Cadena de conexion a la base de datos | `sqlite:///./turnflow.db` |
| `SECRET_KEY` | Firma de JWT | `change-me-use-a-long-random-string` |
| `JWT_ALGORITHM` | Algoritmo de firma | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duracion del token | `480` |
| `REPORTS_DIR` | Carpeta de reportes CSV generados | `reports` |
| `EMAIL_ENABLED` | Activa o desactiva el envio de correos | `false` |
| `EMAIL_SMTP_HOST` | Host SMTP | `smtp.gmail.com` |
| `EMAIL_SMTP_PORT` | Puerto SMTP | `465` |
| `EMAIL_USERNAME` | Usuario SMTP | `usuario@dominio.com` |
| `EMAIL_PASSWORD` | Clave o app password SMTP | `********` |
| `EMAIL_FROM` | Remitente mostrado | `noreply@dominio.com` |
| `EMAIL_SUBJECT_PREFIX` | Prefijo de asunto | `OKÚA Jardín Biosonoro · ` |
| `EMAIL_LOGO_PATH` | Ruta del logo para correos HTML | `static/okua-logo.png` |
| `CHECK_EMAIL_INTERVAL_SECONDS` | Intervalo del scheduler de correos | `60` |

## Ejecución Local

### Windows

```powershell
.\scripts\start_turnflow.bat
```

### Manual

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Luego abre:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`

## Estructura Del Proyecto

- `app/`: lógica principal del backend
- `app/main.py`: API FastAPI, endpoints y scheduler
- `app/auth.py`: autenticación JWT y hashing de contraseñas
- `app/crud.py`: operaciones de datos y reglas de negocio
- `app/models.py`: modelos SQLAlchemy
- `app/schemas.py`: esquemas Pydantic
- `app/database.py`: engine y sesion de BD
- `app/settings.py`: lectura centralizada de entorno
- `static/`: interfaz web y recursos estáticos
- `scripts/`: utilidades de arranque
- `reports/`: salidas CSV generadas en tiempo de ejecución
- `turnflow.db`: base local SQLite generada en desarrollo
- `requirements.txt`: dependencias de runtime

## Comandos Principales

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Comandos útiles del backend:

- `POST /auth/bootstrap-admin`: crear el primer administrador
- `POST /auth/login`: iniciar sesion y obtener JWT
- `GET /health`: comprobación rápida del servicio
- `POST /days/{fecha}/init`: inicializar turnos de un dia
- `POST /reports/daily/{fecha}`: generar reporte CSV

## Notas De Seguridad

- `turnflow.db`, `reports/`, `.venv/` y caches de Python no deben versionarse.
- Los secretos reales van en `.env`; `.env.example` solo contiene valores seguros de ejemplo.
- El frontend guarda el token en `sessionStorage` para reducir persistencia accidental.
- Si las credenciales SMTP o la `SECRET_KEY` estuvieron expuestas en Git, deben rotarse.
- Para despliegue público, usa HTTPS, un proxy inverso y una base de datos gestionada en lugar de SQLite local.

## Despliegue

Este proyecto está listo para ejecución local o despliegue detrás de un proxy inverso.
Antes de publicar:

- configura variables de entorno reales
- desactiva cualquier dato de prueba
- usa una base de datos persistente y segura
- revisa que `EMAIL_ENABLED` solo este activo si el SMTP esta correctamente configurado

## Licencia

No se detecta un archivo de licencia en el repositorio. A falta de una licencia explicita, el codigo debe considerarse con derechos reservados por su autor.
