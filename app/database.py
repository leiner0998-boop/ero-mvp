"""
Configuración de la base de datos.
MVP usa SQLite para que corra en cualquier lado (incluido Termux) sin
depender de un servidor Postgres instalado. Para producción, solo hay
que cambiar DATABASE_URL a una conexión Postgres — SQLAlchemy no cambia.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./ero.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
