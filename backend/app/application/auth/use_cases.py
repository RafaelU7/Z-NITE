"""
Use Cases de autenticação.

Seguindo clean architecture:
  - Use cases não conhecem FastAPI (sem Request/Response HTTP)
  - Recebem dependências via __init__ (testáveis com mocks)
  - Retornam DTOs, nunca modelos ORM
  - Erros de negócio levantam exceções do domínio (app.core.exceptions)
"""
from __future__ import annotations

import uuid

from app.application.auth.dto import (
    LoginRequest,
    LogoutRequest,
    PinLoginRequest,
    RefreshRequest,
    TokenResponse,
    UsuarioPublicoDTO,
)
from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, InvalidTokenError, TokenRevokedError
from app.infrastructure.database.repositories.usuario_repository import UsuarioRepository
from app.infrastructure.security.jwt_handler import (
    TokenPayload,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.infrastructure.security.password_handler import verify_password, verify_pin
from app.infrastructure.security.redis_blacklist import TokenBlacklist

settings = get_settings()


class LoginUseCase:
    """Login com e-mail e senha completa."""

    def __init__(
        self,
        usuario_repo: UsuarioRepository,
        blacklist: TokenBlacklist,
    ) -> None:
        self._repo = usuario_repo
        self._blacklist = blacklist

    async def execute(self, request: LoginRequest) -> TokenResponse:
        user = await self._repo.get_by_email(request.empresa_id, request.email)

        # Verificação unificada: não diferencia "usuário não existe" de "senha errada"
        # para evitar user enumeration.
        if user is None or not verify_password(request.senha, user.senha_hash):
            raise AuthenticationError("Credenciais inválidas")

        await self._repo.update_ultimo_acesso(user.id)

        access_token, _ = create_access_token(user)
        refresh_token, _ = create_refresh_token(user)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )


class PinLoginUseCase:
    """Login rápido por código de operador + PIN (uso no caixa do PDV)."""

    def __init__(self, usuario_repo: UsuarioRepository) -> None:
        self._repo = usuario_repo

    async def execute(self, request: PinLoginRequest) -> TokenResponse:
        user = await self._repo.get_by_codigo_operador(
            request.empresa_id, request.codigo_operador
        )

        if user is None or user.pin_hash is None or not verify_pin(request.pin, user.pin_hash):
            raise AuthenticationError("Código de operador ou PIN inválido")

        await self._repo.update_ultimo_acesso(user.id)

        access_token, _ = create_access_token(user)
        refresh_token, _ = create_refresh_token(user)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )


class RefreshTokenUseCase:
    """
    Renova o par de tokens via refresh token (Token Rotation).
    O refresh token usado é imediatamente invalidado e um novo é emitido.
    """

    def __init__(
        self,
        usuario_repo: UsuarioRepository,
        blacklist: TokenBlacklist,
    ) -> None:
        self._repo = usuario_repo
        self._blacklist = blacklist

    async def execute(self, request: RefreshRequest) -> TokenResponse:
        try:
            payload = decode_token(request.refresh_token)
        except Exception as exc:
            raise InvalidTokenError("Refresh token inválido") from exc

        if payload.type != "refresh":
            raise InvalidTokenError("Token fornecido não é um refresh token")

        if await self._blacklist.is_blacklisted(payload.jti):
            raise TokenRevokedError("Refresh token já foi revogado")

        # Token rotation: invalida imediatamente após uso
        await self._blacklist.add(payload.jti, payload.exp)

        user = await self._repo.get_by_id(uuid.UUID(payload.sub))
        if user is None or not user.ativo:
            raise AuthenticationError("Usuário não encontrado ou inativo")

        access_token, _ = create_access_token(user)
        new_refresh_token, _ = create_refresh_token(user)

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )


class LogoutUseCase:
    """Invalida o access token atual e, opcionalmente, o refresh token."""

    def __init__(self, blacklist: TokenBlacklist) -> None:
        self._blacklist = blacklist

    async def execute(
        self,
        access_payload: TokenPayload,
        request: LogoutRequest | None = None,
    ) -> None:
        await self._blacklist.add(access_payload.jti, access_payload.exp)

        if request and request.refresh_token:
            try:
                refresh_payload = decode_token(request.refresh_token)
                await self._blacklist.add(refresh_payload.jti, refresh_payload.exp)
            except Exception:
                pass  # refresh token inválido/expirado — não há nada a revogar


class GetMeUseCase:
    """Retorna o perfil do usuário autenticado."""

    def __init__(self, usuario_repo: UsuarioRepository) -> None:
        self._repo = usuario_repo

    async def execute(self, user_id: uuid.UUID) -> UsuarioPublicoDTO:
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise AuthenticationError("Usuário não encontrado")
        return UsuarioPublicoDTO.model_validate(user)
