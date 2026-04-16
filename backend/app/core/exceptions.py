"""
Hierarquia de exceções do domínio Zênite PDV.

FastAPI exception handlers em main.py mapeiam cada tipo para o HTTP status correto.
Use cases e repositórios levantam apenas exceções desta hierarquia —
nunca HTTPException diretamente.
"""
from __future__ import annotations


class ZeniteBaseException(Exception):
    """Raiz de todas as exceções de domínio."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__


# ---------------------------------------------------------------------------
# Autenticação / Autorização
# ---------------------------------------------------------------------------


class AuthenticationError(ZeniteBaseException):
    """Credenciais inválidas ou token inválido → HTTP 401."""


class TokenExpiredError(AuthenticationError):
    """JWT expirado → HTTP 401."""


class InvalidTokenError(AuthenticationError):
    """JWT malformado ou assinatura inválida → HTTP 401."""


class TokenRevokedError(AuthenticationError):
    """JWT presente na blacklist (logout) → HTTP 401."""


class AuthorizationError(ZeniteBaseException):
    """Acesso negado por perfil insuficiente → HTTP 403."""


# ---------------------------------------------------------------------------
# Recursos
# ---------------------------------------------------------------------------


class NotFoundError(ZeniteBaseException):
    """Recurso não encontrado → HTTP 404."""


class ConflictError(ZeniteBaseException):
    """Violação de unicidade ou conflito de estado → HTTP 409."""


# ---------------------------------------------------------------------------
# Regras de negócio
# ---------------------------------------------------------------------------


class BusinessRuleError(ZeniteBaseException):
    """Regra de negócio violada → HTTP 422."""


class ValidationError(BusinessRuleError):
    """Dados inválidos segundo regras do domínio → HTTP 422."""


# ---------------------------------------------------------------------------
# Infra / Serviços externos
# ---------------------------------------------------------------------------


class ExternalServiceError(ZeniteBaseException):
    """Erro em serviço externo (SEFAZ, gateway fiscal) → HTTP 502."""


class ServiceUnavailableError(ZeniteBaseException):
    """Dependência crítica indisponível (DB, Redis) → HTTP 503."""
