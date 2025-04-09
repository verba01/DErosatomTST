from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True, echo=False) # echo=True для отладки SQL
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get an async database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit() # Коммит по умолчанию в конце успешной операции
        except Exception as e:
            await session.rollback() # Откат в случае ошибки
            raise e
        finally:
            await session.close()