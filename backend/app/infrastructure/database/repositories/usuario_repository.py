"""
UsuarioRepository — consultas de usuário para autenticação.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.usuario import Usuario
from app.infrastructure.database.repositories.base import BaseRepository


class UsuarioRepository(BaseRepository[Usuario]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Usuario, session)

    async def get_by_email(
        self, empresa_id: uuid.UUID, email: str
    ) -> Optional[Usuario]:
        """Busca usuário ativo por e-mail dentro da empresa."""
        result = await self._session.execute(
            select(Usuario).where(
                Usuario.empresa_id == empresa_id,
                Usuario.email == email,
                Usuario.ativo.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_codigo_operador(
        self, empresa_id: uuid.UUID, codigo_operador: str
    ) -> Optional[Usuario]:
        """
        Busca operador ativo por código curto (login PIN no PDV).
        Retorna apenas usuários com pin_hash configurado.
        """
        result = await self._session.execute(
            select(Usuario).where(
                Usuario.empresa_id == empresa_id,
                Usuario.codigo_operador == codigo_operador,
                Usuario.pin_hash.is_not(None),
                Usuario.ativo.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def update_ultimo_acesso(self, user_id: uuid.UUID) -> None:
        """Registra o timestamp de último acesso (best-effort, sem flush extra)."""
        await self._session.execute(
            update(Usuario)
            .where(Usuario.id == user_id)
            .values(ultimo_acesso=datetime.now(timezone.utc))
        )
