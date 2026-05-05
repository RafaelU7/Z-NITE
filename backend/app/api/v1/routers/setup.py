"""
Router de Setup Inicial — /v1/setup/...

Endpoints públicos (sem autenticação) para primeiro acesso:
  GET  /setup/status   — verifica se empresa já existe
  POST /setup/empresa  — cria empresa + gerente + caixa inicial

Regras:
  - setup_required = true quando nenhuma empresa estiver cadastrada
  - POST /setup/empresa só pode ser chamado uma vez; retorna 409 se já existe empresa
  - Email do gerente é opcional; se vazio, gera e-mail sintético @op.zenite.local
  - razao_social é opcional; se vazio, usa nome_fantasia como razao_social
  - cnpj é opcional (mercados informais podem não ter CNPJ)
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.infrastructure.database.models.caixa import Caixa
from app.infrastructure.database.models.empresa import Empresa
from app.infrastructure.database.models.enums import (
    AmbienteFiscal,
    PerfilUsuario,
    RegimeTributario,
)
from app.infrastructure.database.models.usuario import Usuario
from app.infrastructure.security.password_handler import hash_pin

router = APIRouter(prefix="/setup", tags=["Setup Inicial"])


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


class SetupStatusDTO(BaseModel):
    setup_required: bool
    empresa_id: Optional[str] = None
    empresa_nome: Optional[str] = None


class SetupEmpresaInput(BaseModel):
    nome_fantasia: str = Field(..., min_length=2, max_length=150)
    razao_social: Optional[str] = Field(None, max_length=150)
    cnpj: Optional[str] = Field(None, max_length=14)
    telefone: Optional[str] = Field(None, max_length=15)
    logo_url: Optional[str] = Field(None, max_length=500)

    @field_validator("cnpj", mode="before")
    @classmethod
    def clean_cnpj(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        digits = "".join(c for c in v if c.isdigit())
        return digits if digits else None


class SetupGerenteInput(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150)
    email: Optional[EmailStr] = None
    codigo_operador: str = Field(..., min_length=1, max_length=20)
    pin: str = Field(..., min_length=4, max_length=6)

    @field_validator("pin")
    @classmethod
    def pin_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("PIN deve conter apenas dígitos")
        return v


class SetupEmpresaRequest(BaseModel):
    empresa: SetupEmpresaInput
    gerente: SetupGerenteInput
    caixa_descricao: str = Field("Caixa 01 - Principal", max_length=100)


class SetupEmpresaResponse(BaseModel):
    empresa_id: str
    gerente_id: str
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
    result = await session.execute(
        select(Empresa.id, Empresa.nome_fantasia, Empresa.razao_social).limit(1)
    )
    row = result.first()
    if row is None:
        return SetupStatusDTO(setup_required=True)
    nome = row.nome_fantasia or row.razao_social
    return SetupStatusDTO(
        setup_required=False,
        empresa_id=str(row.id),
        empresa_nome=nome,
    )


@router.post(
    "/empresa",
    response_model=SetupEmpresaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria empresa, gerente e caixa inicial (apenas no primeiro acesso)",
)
async def setup_empresa(
    request: SetupEmpresaRequest,
    session: AsyncSession = Depends(get_async_session),
) -> SetupEmpresaResponse:
    # Idempotência: só roda se nenhuma empresa existe
    result = await session.execute(select(func.count()).select_from(Empresa))
    count = result.scalar() or 0
    if count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sistema já foi inicializado. Use o painel gerencial para alterações.",
        )

    # 1. Empresa
    razao = (request.empresa.razao_social or request.empresa.nome_fantasia).strip()
    empresa = Empresa(
        nome_fantasia=request.empresa.nome_fantasia.strip(),
        razao_social=razao,
        cnpj=request.empresa.cnpj,
        telefone=request.empresa.telefone,
        regime_tributario=RegimeTributario.SIMPLES_NACIONAL,
        ambiente_fiscal=AmbienteFiscal.HOMOLOGACAO,
        ativo=True,
    )
    session.add(empresa)
    await session.flush()  # garante empresa.id

    # 2. Gerente
    email_gerente: str = request.gerente.email or f"{uuid.uuid4().hex[:12]}@op.zenite.local"
    gerente = Usuario(
        empresa_id=empresa.id,
        nome=request.gerente.nome.strip(),
        email=email_gerente,
        senha_hash=hash_pin(request.gerente.pin),  # pin como senha inicial
        perfil=PerfilUsuario.GERENTE,
        codigo_operador=request.gerente.codigo_operador.strip(),
        pin_hash=hash_pin(request.gerente.pin),
        ativo=True,
    )
    session.add(gerente)

    # 3. Caixa padrão
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
    await session.refresh(caixa)

    return SetupEmpresaResponse(
        empresa_id=str(empresa.id),
        gerente_id=str(gerente.id),
        caixa_id=str(caixa.id),
        mensagem=f"Bem-vindo ao Zênite PDV! {empresa.nome_fantasia} configurado com sucesso.",
    )
