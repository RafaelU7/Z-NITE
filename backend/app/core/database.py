"""
Async SQLAlchemy 2.0 — session factory para FastAPI.

Padrão de transação:
  A dependency get_async_session usa session.begin() como context manager,
  que faz commit automático ao final do request e rollback em caso de exceção.
  Use cases chamam session.add() e session.flush() — sem commit explícito.

Alembic continua usando DATABASE_URL (sync psycopg2) via env.py separado.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Engine async — PostgreSQL via asyncpg
# ---------------------------------------------------------------------------
engine = create_async_engine(
    settings.async_database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_pre_ping=True,
    echo=settings.debug,
    connect_args={
        "server_settings": {"timezone": "America/Sao_Paulo"},
    },
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ---------------------------------------------------------------------------
# Dependency para FastAPI — injetada nos endpoints e use cases
# ---------------------------------------------------------------------------
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Abre uma sessão e uma transação.
    - Commit automático ao final do request (sem erros).
    - Rollback automático se qualquer exceção for levantada.
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session
