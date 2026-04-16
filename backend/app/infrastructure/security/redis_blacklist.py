"""
Blacklist de tokens JWT via Redis.

Estratégia:
  - Ao fazer logout, os JTIs do access e refresh tokens são armazenados
    com TTL = tempo restante de validade do token.
  - A verificação é O(1) via EXISTS no Redis.
  - Chave: "zenite:jti:<jti_value>"

Degradação graciful:
  - Se Redis estiver indisponível na verificação, o token é ACEITO (fail-open)
    para garantir disponibilidade do PDV.
  - Erro é sempre logado para alerta operacional.
  - No logout, o erro é propagado (o operador deve ser informado).
"""
from __future__ import annotations

import logging

import redis.asyncio as aioredis

from app.core.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

_KEY_PREFIX = "zenite:jti:"

# Singleton — compartilhado entre requests via pool de conexões
_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """
    Dependency FastAPI e função utilitária.
    Retorna o pool Redis (instância singleton).
    """
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            retry_on_timeout=False,
        )
    return _redis_pool


async def close_redis() -> None:
    """Fecha o pool Redis (chamado no shutdown da aplicação)."""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.aclose()
        _redis_pool = None


class TokenBlacklist:
    """Gerencia a blacklist de JTIs revogados no Redis."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    async def add(self, jti: str, exp_timestamp: int) -> None:
        """
        Adiciona jti à blacklist com TTL automático.
        Se o token já expirou, não há nada a fazer.
        """
        from datetime import datetime, timezone

        now = int(datetime.now(timezone.utc).timestamp())
        ttl = exp_timestamp - now
        if ttl <= 0:
            return
        await self._redis.setex(f"{_KEY_PREFIX}{jti}", ttl, "1")

    async def is_blacklisted(self, jti: str) -> bool:
        """
        Retorna True se o JTI estiver na blacklist.
        Em caso de falha do Redis, retorna False (fail-open) e loga o erro.
        """
        try:
            return bool(await self._redis.exists(f"{_KEY_PREFIX}{jti}"))
        except Exception as exc:
            log.warning(
                "Redis indisponível ao verificar blacklist de token (jti=%s): %s",
                jti,
                exc,
            )
            return False  # fail-open: PDV não pode parar por Redis offline
