import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from pressao_api.core.config import settings

logger = structlog.get_logger()

# Converte URL para async
DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Detecta se é PostgreSQL ou SQLite
is_postgres = "postgresql" in DATABASE_URL or "asyncpg" in DATABASE_URL

# Cria a engine
if is_postgres:
    engine = create_async_engine(
        DATABASE_URL,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        echo=settings.DEBUG,
    )
else:
    # Para SQLite, usamos NullPool para evitar problemas
    engine = create_async_engine(
        DATABASE_URL,
        poolclass=NullPool,
        echo=settings.DEBUG,
    )

logger.info(f"Engine criada para {'PostgreSQL' if is_postgres else 'SQLite'}")

# Session local
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db():
    """Dependência para obter sessão do banco."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
