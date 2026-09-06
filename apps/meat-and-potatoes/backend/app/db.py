"""SQLAlchemy engine + session plumbing."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
engine = create_engine(
    _settings.db_url,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Create tables and seed the singleton profile row."""
    from . import models  # noqa: F401  (register mappers)

    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.get(models.Profile, 1) is None:
            db.add(models.Profile(id=1, data={}))
            db.commit()


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
