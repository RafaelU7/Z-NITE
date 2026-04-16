"""
Router de sincronização offline — /v1/sync/...

POST /sync/vendas
  Recebe um lote de vendas finalizadas offline e as integra ao sistema.

  Processamento por venda:
    - aceita   → nova venda criada, documento fiscal PENDENTE gerado
    - duplicada → chave_idempotencia já existente (idempotente, sem erro)
    - rejeitada → violação de regra de negócio ou dado inválido

  Cada venda é comitada individualmente para garantir que erros parciais
  não rejeitem o lote inteiro.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sync.dto import SyncBatchRequest, SyncBatchResponse
from app.application.sync.use_cases import SincronizarVendasUseCase
from app.application.fiscal.services.fiscal_service import FiscalService
from app.core.database import get_async_session
from app.core.dependencies import get_current_user, get_empresa_id
from app.infrastructure.database.models.usuario import Usuario
from app.infrastructure.database.repositories.caixa_repository import CaixaRepository
from app.infrastructure.database.repositories.estoque_repository import EstoqueRepository
from app.infrastructure.database.repositories.fiscal_repository import FiscalRepository
from app.infrastructure.database.repositories.produto_repository import ProdutoRepository
from app.infrastructure.database.repositories.venda_repository import VendaRepository

router = APIRouter(prefix="/sync", tags=["Sincronização Offline"])


async def _enqueue_fiscal_job(arq_pool, documento_id: str) -> None:
    await arq_pool.enqueue_job(
        "processar_documento_fiscal",
        documento_id,
        _queue_name="arq:zenite_fiscal",
        _job_id=f"fiscal-{documento_id}",
    )


@router.post(
    "/vendas",
    response_model=SyncBatchResponse,
    summary="Sincronizar lote de vendas offline",
    description=(
        "Recebe vendas finalizadas no PDV enquanto offline e as integra ao backend. "
        "Usa chave_idempotencia para deduplicação — reenvios são seguros. "
        "Retorna listas de aceitas, duplicadas e rejeitadas."
    ),
)
async def sincronizar_vendas(
    request: SyncBatchRequest,
    http_request: Request,
    background_tasks: BackgroundTasks,
    current_user: Usuario = Depends(get_current_user),
    empresa_id: UUID = Depends(get_empresa_id),
    session: AsyncSession = Depends(get_async_session),
) -> SyncBatchResponse:
    response = await SincronizarVendasUseCase(
        session=session,
        venda_repo=VendaRepository(session),
        caixa_repo=CaixaRepository(session),
        produto_repo=ProdutoRepository(session),
        estoque_repo=EstoqueRepository(session),
        fiscal_service=FiscalService(fiscal_repo=FiscalRepository(session)),
    ).execute(
        request=request,
        empresa_id=empresa_id,
        operador_id=current_user.id,
    )

    arq_pool = getattr(http_request.app.state, "arq_pool", None)
    if arq_pool is not None:
        for aceita in response.aceitas:
            if aceita.documento_fiscal_id is not None:
                background_tasks.add_task(
                    _enqueue_fiscal_job,
                    arq_pool,
                    str(aceita.documento_fiscal_id),
                )

    return response
