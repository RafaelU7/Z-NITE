"""
FastAPI Dependency Injection — autenticação, sessão e permissões.

Dependências disponíveis:
  - get_async_session      → AsyncSession (re-exportada de database.py)
  - get_current_token      → TokenPayload validado (blacklist verificada)
  - get_current_user       → Usuario ORM (ativo, do banco)
  - get_empresa_id         → UUID da empresa do usuário autenticado
  - require_perfil(perfil) → factory que exige nível mínimo de perfil
"""
from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    TokenRevokedError,
)
from app.infrastructure.database.models.enums import PerfilUsuario
from app.infrastructure.database.models.usuario import Usuario
from app.infrastructure.database.repositories.usuario_repository import UsuarioRepository
from app.infrastructure.security.jwt_handler import TokenPayload, decode_token
from app.infrastructure.security.redis_blacklist import TokenBlacklist, get_redis

_security = HTTPBearer(auto_error=False)

# Hierarquia de perfis: maior índice = mais privilegiado
_PERFIL_NIVEL: dict[PerfilUsuario, int] = {
    PerfilUsuario.OPERADOR_CAIXA: 0,
    PerfilUsuario.ESTOQUISTA: 1,
    PerfilUsuario.GERENTE: 2,
    PerfilUsuario.ADMIN: 3,
    PerfilUsuario.SUPER_ADMIN: 4,
}


async def get_current_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
    redis=Depends(get_redis),
) -> TokenPayload:
    """
    Valida o Bearer token e verifica blacklist Redis.
    Retorna TokenPayload — útil para endpoints que precisam do jti (ex: logout).
    """
    if credentials is None:
        raise AuthenticationError("Token de autenticação não fornecido")

    payload = decode_token(credentials.credentials)

    blacklist = TokenBlacklist(redis)
    if await blacklist.is_blacklisted(payload.jti):
        raise TokenRevokedError("Token revogado")

    return payload


async def get_current_user(
    payload: TokenPayload = Depends(get_current_token),
    session: AsyncSession = Depends(get_async_session),
) -> Usuario:
    """Retorna o usuário ORM autenticado e ativo."""
    repo = UsuarioRepository(session)
    user = await repo.get_by_id(uuid.UUID(payload.sub))
    if user is None or not user.ativo:
        raise AuthenticationError("Usuário não encontrado ou inativo")
    return user


async def get_empresa_id(
    current_user: Usuario = Depends(get_current_user),
) -> uuid.UUID:
    """Extrai empresa_id do usuário autenticado."""
    return current_user.empresa_id


def require_perfil(min_perfil: PerfilUsuario) -> Callable:
    """
    Factory de dependency que exige perfil mínimo.

    Uso:
        @router.delete("/produto/{id}", dependencies=[Depends(require_perfil(PerfilUsuario.GERENTE))])
        ou como parâmetro tipado:
        async def endpoint(user: Usuario = Depends(require_perfil(PerfilUsuario.ADMIN))):
    """
    async def _check(user: Usuario = Depends(get_current_user)) -> Usuario:
        nivel_user = _PERFIL_NIVEL.get(PerfilUsuario(user.perfil), -1)
        nivel_req = _PERFIL_NIVEL.get(min_perfil, 0)
        if nivel_user < nivel_req:
            raise AuthorizationError(
                f"Acesso negado. Perfil requerido: {min_perfil.value}"
            )
        return user

    return _check
