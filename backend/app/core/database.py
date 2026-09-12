"""SQLAlchemy（非同期）の設定。DB は Docker の PostgreSQL 16（docker-compose.yml）。"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """ORM モデルの基底（④ のテーブル8つがこれを継承する）。"""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """リクエストごとのセッション。"""
    async with AsyncSessionLocal() as session:
        yield session
