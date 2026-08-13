"""数据库引擎与会话工厂（SQLAlchemy Async）。"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    """所有 ORM 模型的声明基类。"""

    pass


settings = get_settings()
engine = create_async_engine(settings.database_url, echo=settings.debug)
# expire_on_commit=False：提交后仍可访问已加载属性，避免异步场景懒加载问题
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：请求级会话，退出时自动关闭。"""
    async with SessionLocal() as session:
        yield session
