from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _get_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} debe ser un número entero.") from exc


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./turnflow.db")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-env")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = _get_int_env("ACCESS_TOKEN_EXPIRE_MINUTES", 8 * 60)

REPORTS_DIR = os.getenv("REPORTS_DIR", "reports")

EMAIL_ENABLED = _get_bool_env("EMAIL_ENABLED", False)
EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
EMAIL_SMTP_PORT = _get_int_env("EMAIL_SMTP_PORT", 465)
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM") or EMAIL_USERNAME
EMAIL_SUBJECT_PREFIX = os.getenv("EMAIL_SUBJECT_PREFIX", "OKÚA Jardín Biosonoro · ")
EMAIL_LOGO_PATH = os.getenv("EMAIL_LOGO_PATH", "static/okua-logo.png")

CHECK_EMAIL_INTERVAL_SECONDS = _get_int_env("CHECK_EMAIL_INTERVAL_SECONDS", 60)
