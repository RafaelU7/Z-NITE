"""
Router de Venda / PDV — /v1/vendas/...

Endpoints:
  POST   /                         — inicia nova venda
  GET    /{venda_id}               — detalha venda (itens + pagamentos)
  POST   /{venda_id}/itens         — adiciona item à venda
  DELETE /{venda_id}/itens/{item_id} — cancela item (estorno de estoque)
  POST   /{venda_id}/pagamentos    — adiciona forma de pagamento
  POST   /{venda_id}/finalizar     — conclui venda (cria DocumentoFiscal pendente)
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.venda.dto import (
    AdicionarItemRequest,
    AdicionarPagamentoRequest,
    FinalizarVendaRequest,
    IniciarVendaRequest,
    VendaDTO,
)
from app.application.venda.use_cases import (
    AdicionarItemUseCase,
    AdicionarPagamentoUseCase,
    FinalizarVendaUseCase,
    GetVendaUseCase,
    IniciarVendaUseCase,
    RemoverItemUseCase,
)
from app.application.fiscal.services.fiscal_service import FiscalService
from app.core.database import get_async_session
from app.core.dependencies import get_current_user, get_empresa_id
from app.infrastructure.database.models.usuario import Usuario
from app.infrastructure.database.repositories.caixa_repository import CaixaRepository
from app.infrastructure.database.repositories.estoque_repository import EstoqueRepository
from app.infrastructure.database.repositories.fiscal_repository import FiscalRepository
from app.infrastructure.database.repositories.produto_repository import ProdutoRepository
from app.infrastructure.database.repositories.venda_repository import VendaRepository

router = APIRouter(prefix="/vendas", tags=["Venda / PDV"])


@router.post(
    "/",
    response_model=VendaDTO,
    status_code=201,
    summary="Iniciar nova venda",
)
async def iniciar_venda(
    request: IniciarVendaRequest,
    current_user: Usuario = Depends(get_current_user),
    empresa_id: UUID = Depends(get_empresa_id),
    session: AsyncSession = Depends(get_async_session),
) -> VendaDTO:
    return await IniciarVendaUseCase(
        venda_repo=VendaRepository(session),
        caixa_repo=CaixaRepository(session),
    ).execute(
        request=request,
        empresa_id=empresa_id,
        operador_id=current_user.id,
    )


@router.get(
    "/{venda_id}",
    response_model=VendaDTO,
    summary="Detalhar venda (itens + pagamentos)",
)
async def get_venda(
    venda_id: UUID,
    empresa_id: UUID = Depends(get_empresa_id),
    session: AsyncSession = Depends(get_async_session),
) -> VendaDTO:
    return await GetVendaUseCase(
        repo=VendaRepository(session),
    ).execute(venda_id=venda_id, empresa_id=empresa_id)


@router.post(
    "/{venda_id}/itens",
    response_model=VendaDTO,
    status_code=201,
    summary="Adicionar item à venda",
)
async def adicionar_item(
    venda_id: UUID,
    request: AdicionarItemRequest,
    current_user: Usuario = Depends(get_current_user),
    empresa_id: UUID = Depends(get_empresa_id),
    session: AsyncSession = Depends(get_async_session),
) -> VendaDTO:
    return await AdicionarItemUseCase(
        venda_repo=VendaRepository(session),
        produto_repo=ProdutoRepository(session),
        estoque_repo=EstoqueRepository(session),
    ).execute(
        venda_id=venda_id,
        request=request,
        empresa_id=empresa_id,
        operador_id=current_user.id,
    )


@router.delete(
    "/{venda_id}/itens/{item_id}",
    response_model=VendaDTO,
    summary="Cancelar item da venda (restaura estoque)",
)
async def remover_item(
    venda_id: UUID,
    item_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    empresa_id: UUID = Depends(get_empresa_id),
    session: AsyncSession = Depends(get_async_session),
) -> VendaDTO:
    return await RemoverItemUseCase(
        venda_repo=VendaRepository(session),
        estoque_repo=EstoqueRepository(session),
    ).execute(
        venda_id=venda_id,
        item_id=item_id,
        empresa_id=empresa_id,
        operador_id=current_user.id,
    )


@router.post(
    "/{venda_id}/pagamentos",
    response_model=VendaDTO,
    status_code=201,
    summary="Adicionar forma de pagamento",
)
async def adicionar_pagamento(
    venda_id: UUID,
    request: AdicionarPagamentoRequest,
    empresa_id: UUID = Depends(get_empresa_id),
    session: AsyncSession = Depends(get_async_session),
) -> VendaDTO:
    return await AdicionarPagamentoUseCase(
        repo=VendaRepository(session),
    ).execute(
        venda_id=venda_id,
        request=request,
        empresa_id=empresa_id,
    )


@router.post(
    "/{venda_id}/finalizar",
    response_model=VendaDTO,
    summary="Finalizar venda (FISCAL cria DocumentoFiscal pendente; GERENCIAL só registra)",
)
async def finalizar_venda(
    venda_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: Usuario = Depends(get_current_user),
    empresa_id: UUID = Depends(get_empresa_id),
    session: AsyncSession = Depends(get_async_session),
    body: FinalizarVendaRequest = Body(default=None),
    http_request: Request = None,
) -> VendaDTO:
    fiscal_service = FiscalService(
        fiscal_repo=FiscalRepository(session),
    )
    venda = await FinalizarVendaUseCase(
        venda_repo=VendaRepository(session),
        estoque_repo=EstoqueRepository(session),
        fiscal_service=fiscal_service,
    ).execute(
        venda_id=venda_id,
        empresa_id=empresa_id,
        operador_id=current_user.id,
        tipo_emissao=(body.tipo_emissao if body else FinalizarVendaRequest().tipo_emissao),
    )

    # Enfileira processamento fiscal SOMENTE para vendas FISCAL com documento gerado
    if venda.documento_fiscal_id is not None:
        arq_pool = None
        if http_request is not None:
            arq_pool = getattr(http_request.app.state, "arq_pool", None)
        if arq_pool is not None:
            doc_id_str = str(venda.documento_fiscal_id)
            background_tasks.add_task(
                _enqueue_fiscal_job,
                arq_pool,
                doc_id_str,
            )

    return venda


async def _enqueue_fiscal_job(arq_pool, documento_id: str) -> None:
    """Enfileira o job ARQ de processamento fiscal."""
    await arq_pool.enqueue_job(
        "processar_documento_fiscal",
        documento_id,
        _queue_name="arq:zenite_fiscal",
        _job_id=f"fiscal-{documento_id}",
    )
