from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, autoflush=False, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db
