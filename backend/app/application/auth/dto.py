"""
DTOs de autenticação — contratos de entrada e saída da API de auth.

Nenhum modelo SQLAlchemy é exposto diretamente.
Todos os campos sensíveis (senha, pin) ficam apenas nos Request DTOs
e nunca aparecem em Response DTOs.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.infrastructure.database.models.enums import PerfilUsuario


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    empresa_id: uuid.UUID
    email: EmailStr
    senha: str = Field(..., min_length=6, max_length=200)


class PinLoginRequest(BaseModel):
    empresa_id: uuid.UUID
    codigo_operador: str = Field(..., min_length=1, max_length=20)
    pin: str = Field(..., min_length=4, max_length=6)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    """Permite revogar também o refresh token no logout."""
    refresh_token: Optional[str] = None


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos até expiração do access token


class UsuarioPublicoDTO(BaseModel):
    """Perfil público do usuário autenticado — nunca expõe hash de senha/pin."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    email: str
    perfil: PerfilUsuario
    empresa_id: uuid.UUID
    codigo_operador: Optional[str]
    ultimo_acesso: Optional[datetime]
    ativo: bool
