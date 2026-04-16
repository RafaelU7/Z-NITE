"""
Geração e validação de tokens JWT.

Estrutura do payload:
  sub        : ID do usuário (UUID como string)
  empresa_id : UUID da empresa (multi-tenant)
  perfil     : perfil do usuário (ex: "gerente")
  nome       : nome legível para o frontend
  jti        : UUID único do token — chave para blacklist de logout
  type       : "access" | "refresh"
  iat / exp  : timestamps Unix (int)

Access token  : expira em ACCESS_TOKEN_EXPIRE_MINUTES (padrão 8h)
Refresh token : expira em REFRESH_TOKEN_EXPIRE_DAYS (padrão 30d)
  — Refresh token rotation: cada uso gera um novo par e invalida o antigo.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from jose import ExpiredSignatureError, JWTError
from jose import jwt as jose_jwt
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.exceptions import InvalidTokenError, TokenExpiredError

settings = get_settings()


# ---------------------------------------------------------------------------
# Payload model
# ---------------------------------------------------------------------------


class TokenPayload(BaseModel):
    sub: str          # user UUID
    empresa_id: str   # empresa UUID
    perfil: str       # PerfilUsuario value
    nome: str
    jti: str          # JWT ID para blacklist
    type: str         # "access" | "refresh"
    iat: int          # issued-at (Unix timestamp)
    exp: int          # expiry (Unix timestamp)


# ---------------------------------------------------------------------------
# Internos
# ---------------------------------------------------------------------------


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _build_token(
    user_id: uuid.UUID,
    empresa_id: uuid.UUID,
    perfil: str,
    nome: str,
    token_type: str,
    expires_delta: timedelta,
) -> tuple[str, str]:
    """Cria o JWT e retorna (token_string, jti)."""
    jti = str(uuid.uuid4())
    now = _now_utc()
    expire = now + expires_delta

    payload = {
        "sub": str(user_id),
        "empresa_id": str(empresa_id),
        "perfil": perfil,
        "nome": nome,
        "jti": jti,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    token = jose_jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token, jti


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def create_access_token(user: "Usuario") -> tuple[str, str]:  # type: ignore[name-defined]
    """Retorna (access_token, jti)."""
    delta = timedelta(minutes=settings.access_token_expire_minutes)
    return _build_token(
        user_id=user.id,
        empresa_id=user.empresa_id,
        perfil=str(user.perfil),
        nome=user.nome,
        token_type="access",
        expires_delta=delta,
    )


def create_refresh_token(user: "Usuario") -> tuple[str, str]:  # type: ignore[name-defined]
    """Retorna (refresh_token, jti)."""
    delta = timedelta(days=settings.refresh_token_expire_days)
    return _build_token(
        user_id=user.id,
        empresa_id=user.empresa_id,
        perfil=str(user.perfil),
        nome=user.nome,
        token_type="refresh",
        expires_delta=delta,
    )


def decode_token(token: str) -> TokenPayload:
    """
    Decodifica e valida um JWT.

    Raises:
        TokenExpiredError  : token expirado
        InvalidTokenError  : assinatura inválida ou payload corrompido
    """
    try:
        raw = jose_jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
    except ExpiredSignatureError as exc:
        raise TokenExpiredError("Token expirado") from exc
    except JWTError as exc:
        raise InvalidTokenError(f"Token inválido: {exc}") from exc

    try:
        return TokenPayload(**raw)
    except Exception as exc:
        raise InvalidTokenError("Payload do token malformado") from exc
