from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .settings import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clase base para los modelos
Base = declarative_base()


def get_db():
    """
    Dependencia para FastAPI.
    Abre una sesión a la BD y la cierra automáticamente al terminar la petición.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
