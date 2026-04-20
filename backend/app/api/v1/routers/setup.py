"""
Router de Setup Inicial — /v1/setup/...

Endpoints públicos (sem autenticação) para primeiro acesso:
  GET  /setup/status        — verifica se empresa já existe
  POST /setup/inicializar   — cria empresa + gerente + operador + caixa inicial
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.infrastructure.database.models.caixa import Caixa
from app.infrastructure.database.models.empresa import Empresa
from app.infrastructure.database.models.enums import (
    AmbienteFiscal,
    PerfilUsuario,
    RegimeTributario,
    StatusSessaoCaixa,
)
from app.infrastructure.database.models.usuario import Usuario
from app.infrastructure.security.password_handler import hash_password, hash_pin

router = APIRouter(prefix="/setup", tags=["Setup Inicial"])


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


class SetupStatusDTO(BaseModel):
    necessita_setup: bool


class SetupEmpresaInput(BaseModel):
    razao_social: str = Field(..., min_length=2, max_length=150)
    nome_fantasia: Optional[str] = Field(None, max_length=150)
    cnpj: str = Field(..., min_length=11, max_length=14, pattern=r"^\d{11,14}$")
    regime_tributario: RegimeTributario = RegimeTributario.SIMPLES_NACIONAL


class SetupGerenteInput(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    senha: str = Field(..., min_length=6, max_length=200)
    codigo_operador: str = Field(..., min_length=1, max_length=20)
    pin: str = Field(..., min_length=4, max_length=6)


class SetupOperadorInput(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    codigo_operador: str = Field(..., min_length=1, max_length=20)
    pin: str = Field(..., min_length=4, max_length=6)


class SetupInicializarRequest(BaseModel):
    empresa: SetupEmpresaInput
    gerente: SetupGerenteInput
    operador: SetupOperadorInput
    caixa_descricao: str = Field("Caixa Principal", max_length=100)


class SetupInicializarResponse(BaseModel):
    empresa_id: str
    gerente_id: str
    operador_id: str
    caixa_id: str
    mensagem: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/status",
    response_model=SetupStatusDTO,
    summary="Verifica se o sistema precisa de configuração inicial",
)
async def get_setup_status(
    session: AsyncSession = Depends(get_async_session),
) -> SetupStatusDTO:
    result = await session.execute(select(func.count()).select_from(Empresa))
    count = result.scalar() or 0
    return SetupStatusDTO(necessita_setup=count == 0)


@router.post(
    "/inicializar",
    response_model=SetupInicializarResponse,
    status_code=201,
    summary="Cria empresa, gerente, operador e caixa inicial",
)
async def inicializar_sistema(
    request: SetupInicializarRequest,
    session: AsyncSession = Depends(get_async_session),
) -> SetupInicializarResponse:
    # Garante idempotência — só roda se não existe empresa
    result = await session.execute(select(func.count()).select_from(Empresa))
    count = result.scalar() or 0
    if count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sistema já foi inicializado. Use o painel gerencial para alterações.",
        )

    cnpj_limpo = request.empresa.cnpj.replace(".", "").replace("/", "").replace("-", "")

    # 1. Empresa
    empresa = Empresa(
        razao_social=request.empresa.razao_social,
        nome_fantasia=request.empresa.nome_fantasia,
        cnpj=cnpj_limpo,
        regime_tributario=request.empresa.regime_tributario,
        ambiente_fiscal=AmbienteFiscal.HOMOLOGACAO,
    )
    session.add(empresa)
    await session.flush()  # gera empresa.id

    # 2. Gerente
    gerente = Usuario(
        empresa_id=empresa.id,
        nome=request.gerente.nome,
        email=request.gerente.email,
        senha_hash=hash_password(request.gerente.senha),
        perfil=PerfilUsuario.GERENTE,
        codigo_operador=request.gerente.codigo_operador,
        pin_hash=hash_pin(request.gerente.pin),
        ativo=True,
    )
    session.add(gerente)

    # 3. Operador
    operador = Usuario(
        empresa_id=empresa.id,
        nome=request.operador.nome,
        email=request.operador.email,
        senha_hash=hash_password(request.operador.pin),  # usa pin como senha inicial
        perfil=PerfilUsuario.OPERADOR_CAIXA,
        codigo_operador=request.operador.codigo_operador,
        pin_hash=hash_pin(request.operador.pin),
        ativo=True,
    )
    session.add(operador)

    # 4. Caixa
    caixa = Caixa(
        empresa_id=empresa.id,
        numero=1,
        descricao=request.caixa_descricao,
        ativo=True,
    )
    session.add(caixa)

    await session.commit()
    await session.refresh(empresa)
    await session.refresh(gerente)
    await session.refresh(operador)
    await session.refresh(caixa)

    return SetupInicializarResponse(
        empresa_id=str(empresa.id),
        gerente_id=str(gerente.id),
        operador_id=str(operador.id),
        caixa_id=str(caixa.id),
        mensagem="Sistema inicializado com sucesso.",
    )
