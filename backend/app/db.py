from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

# Normalize postgresql:// scheme to postgresql+psycopg2:// if needed
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# SQLite fallback support for in-memory unit tests if used
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a SQLAlchemy database session."""
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
