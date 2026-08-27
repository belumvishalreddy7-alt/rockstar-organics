"""SQLAlchemy engine, session factory, and declarative base."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if _is_sqlite else {}

# Serverless hosts (e.g. Vercel Python functions) run many short-lived
# process instances rather than one long-lived server, so a large per-process
# pool just wastes connections against the database's (or pooler's) client
# limit. pool_pre_ping guards against a pooler (e.g. Supabase's Supavisor)
# silently recycling an idle backend connection out from under us.
engine_kwargs: dict = {"connect_args": connect_args, "future": True, "pool_pre_ping": True}
if not _is_sqlite:
    engine_kwargs.update(pool_size=1, max_overflow=2, pool_recycle=300)

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
