from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Support both SQLite (local dev) and PostgreSQL (production on Render)
DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "hiram_group.db")
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    _connect_args = {"check_same_thread": False}
else:
    # Render provides postgres:// but SQLAlchemy needs postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    _connect_args = {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from backend.models import Base as ModelsBase
    ModelsBase.metadata.create_all(bind=engine)
