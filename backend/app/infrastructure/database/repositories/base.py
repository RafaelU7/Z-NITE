"""
BaseRepository genérico — SQLAlchemy 2.0 async.

Todos os repositórios do sistema herdam desta classe para operações CRUD básicas.
Operações específicas de domínio são adicionadas nas subclasses.
"""
from __future__ import annotations

from typing import Generic, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    def __init__(self, model: Type[ModelT], session: AsyncSession) -> None:
        self._model = model
        self._session = session

    async def get_by_id(self, id: UUID) -> Optional[ModelT]:
        """Busca por PK (UUID). Retorna None se não encontrado."""
        result = await self._session.execute(
            select(self._model).where(self._model.id == id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def save(self, obj: ModelT) -> ModelT:
        """
        Persiste o objeto na sessão atual (sem commit — gerenciado pelo dep).
        flush() garante que IDs gerados pelo banco fiquem disponíveis.
        """
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        """Remove o objeto. flush() propaga antes do commit."""
        await self._session.delete(obj)
        await self._session.flush()
