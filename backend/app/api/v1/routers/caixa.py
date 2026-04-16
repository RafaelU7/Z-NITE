"""
Router de Caixa — /v1/caixa/...

Endpoints:
  POST /sessoes                      — abre nova sessão de caixa
  GET  /sessao-ativa                 — retorna sessão aberta do caixa (?caixa_id=)
  POST /sessoes/{sessao_id}/fechar   — fecha a sessão e calcula totais
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.caixa.dto import AbrirSessaoRequest, FecharSessaoRequest, SessaoCaixaDTO
from app.application.caixa.use_cases import (
    AbrirSessaoUseCase,
    FecharSessaoUseCase,
    GetSessaoAtivaUseCase,
)
from app.core.database import get_async_session
from app.core.dependencies import get_current_user, get_empresa_id
from app.infrastructure.database.models.usuario import Usuario
from app.infrastructure.database.repositories.caixa_repository import CaixaRepository

router = APIRouter(prefix="/caixa", tags=["Caixa"])


@router.post(
    "/sessoes",
    response_model=SessaoCaixaDTO,
    status_code=201,
    summary="Abrir sessão de caixa (início de turno)",
)
async def abrir_sessao(
    request: AbrirSessaoRequest,
    current_user: Usuario = Depends(get_current_user),
    empresa_id: UUID = Depends(get_empresa_id),
    session: AsyncSession = Depends(get_async_session),
) -> SessaoCaixaDTO:
    return await AbrirSessaoUseCase(
        repo=CaixaRepository(session),
    ).execute(
        request=request,
        empresa_id=empresa_id,
        operador_id=current_user.id,
    )


@router.get(
    "/sessao-ativa",
    response_model=SessaoCaixaDTO,
    summary="Retorna a sessão aberta de um caixa",
)
async def get_sessao_ativa(
    caixa_id: UUID,
    empresa_id: UUID = Depends(get_empresa_id),
    session: AsyncSession = Depends(get_async_session),
) -> SessaoCaixaDTO:
    return await GetSessaoAtivaUseCase(
        repo=CaixaRepository(session),
    ).execute(caixa_id=caixa_id, empresa_id=empresa_id)


@router.post(
    "/sessoes/{sessao_id}/fechar",
    response_model=SessaoCaixaDTO,
    summary="Fechar sessão de caixa (fim de turno)",
)
async def fechar_sessao(
    sessao_id: UUID,
    request: FecharSessaoRequest,
    current_user: Usuario = Depends(get_current_user),
    empresa_id: UUID = Depends(get_empresa_id),
    session: AsyncSession = Depends(get_async_session),
) -> SessaoCaixaDTO:
    return await FecharSessaoUseCase(
        repo=CaixaRepository(session),
    ).execute(
        sessao_id=sessao_id,
        request=request,
        empresa_id=empresa_id,
        operador_fechamento_id=current_user.id,
    )
