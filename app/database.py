"""
Database engine and session factory — async SQLAlchemy.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,     # cek koneksi sebelum dipakai, auto-reconnect jika mati
    pool_recycle=1800,      # buang koneksi yang >30 menit (sebelum Neon timeout)
    pool_size=5,
    max_overflow=10,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    """Dependency: yields an async DB session."""
    async with async_session() as session:
        yield session
