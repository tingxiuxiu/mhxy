from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from .config import settings


def _create_engine():
    """根据数据库类型创建engine，SQLite不支持连接池参数"""
    connect_args = {}
    kwargs = {
        "echo": settings.DATABASE_ECHO,
        "pool_pre_ping": True,
    }
    if settings.DATABASE_URL.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        kwargs["connect_args"] = connect_args
    else:
        kwargs["pool_size"] = 20
        kwargs["max_overflow"] = 30
    return create_async_engine(settings.DATABASE_URL, **kwargs)


engine = _create_engine()

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
