"""
Router de autenticação — POST /v1/auth/...

Endpoints:
  POST /login        — e-mail + senha → access_token + refresh_token
  POST /pin-login    — codigo_operador + PIN → tokens (uso no caixa PDV)
  POST /refresh      — troca refresh_token por novo par (token rotation)
  POST /logout       — revoga access + (opcional) refresh via blacklist Redis
  GET  /me           — perfil do usuário autenticado
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.auth.dto import (
    LoginRequest,
    LogoutRequest,
    PinLoginRequest,
    RefreshRequest,
    TokenResponse,
    UsuarioPublicoDTO,
)
from app.application.auth.use_cases import (
    GetMeUseCase,
    LoginUseCase,
    LogoutUseCase,
    PinLoginUseCase,
    RefreshTokenUseCase,
)
from app.core.database import get_async_session
from app.core.dependencies import get_current_token, get_current_user
from app.infrastructure.database.models.usuario import Usuario
from app.infrastructure.database.repositories.usuario_repository import UsuarioRepository
from app.infrastructure.security.jwt_handler import TokenPayload
from app.infrastructure.security.redis_blacklist import TokenBlacklist, get_redis

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login com e-mail e senha",
)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_async_session),
    redis=Depends(get_redis),
) -> TokenResponse:
    return await LoginUseCase(
        usuario_repo=UsuarioRepository(session),
        blacklist=TokenBlacklist(redis),
    ).execute(request)


@router.post(
    "/pin-login",
    response_model=TokenResponse,
    summary="Login rápido por código de operador + PIN (caixa PDV)",
)
async def pin_login(
    request: PinLoginRequest,
    session: AsyncSession = Depends(get_async_session),
) -> TokenResponse:
    return await PinLoginUseCase(
        usuario_repo=UsuarioRepository(session),
    ).execute(request)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renovar par de tokens (Token Rotation)",
)
async def refresh_token(
    request: RefreshRequest,
    session: AsyncSession = Depends(get_async_session),
    redis=Depends(get_redis),
) -> TokenResponse:
    return await RefreshTokenUseCase(
        usuario_repo=UsuarioRepository(session),
        blacklist=TokenBlacklist(redis),
    ).execute(request)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Invalidar tokens (logout)",
)
async def logout(
    body: LogoutRequest | None = None,
    payload: TokenPayload = Depends(get_current_token),
    redis=Depends(get_redis),
) -> None:
    await LogoutUseCase(blacklist=TokenBlacklist(redis)).execute(
        access_payload=payload,
        request=body,
    )


@router.get(
    "/me",
    response_model=UsuarioPublicoDTO,
    summary="Perfil do usuário autenticado",
)
async def get_me(
    current_user: Usuario = Depends(get_current_user),
) -> UsuarioPublicoDTO:
    return UsuarioPublicoDTO.model_validate(current_user)
