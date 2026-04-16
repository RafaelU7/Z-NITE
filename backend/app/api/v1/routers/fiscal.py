"""
Router Fiscal — /v1/fiscal/...

Endpoints:
  GET  /vendas/{venda_id}/documento          — documento fiscal da venda
  GET  /documentos/{doc_id}/status           — status do documento fiscal
  POST /documentos/{doc_id}/reprocessar      — marca PENDENTE + re-enfileira job
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.fiscal.dto import DocumentoFiscalDTO
from app.application.fiscal.use_cases import (
    ConsultarStatusDocumentoUseCase,
    GetDocumentoPorVendaUseCase,
    ReprocessarDocumentoUseCase,
)
from app.core.database import get_async_session
from app.core.dependencies import get_current_user, get_empresa_id
from app.infrastructure.database.repositories.fiscal_repository import FiscalRepository

router = APIRouter(prefix="/fiscal", tags=["Fiscal"])


async def _enqueue_fiscal_job(arq_pool, documento_id: str) -> None:
    """Enfileira o job de processamento fiscal. Executado em BackgroundTask."""
    await arq_pool.enqueue_job(
        "processar_documento_fiscal",
        documento_id,
        _queue_name="arq:zenite_fiscal",
        _job_id=f"fiscal-{documento_id}",
    )


@router.get(
    "/vendas/{venda_id}/documento",
    response_model=DocumentoFiscalDTO,
    summary="Documento fiscal da venda",
)
async def get_documento_por_venda(
    venda_id: UUID,
    empresa_id: UUID = Depends(get_empresa_id),
    session: AsyncSession = Depends(get_async_session),
    _user=Depends(get_current_user),
) -> DocumentoFiscalDTO:
    return await GetDocumentoPorVendaUseCase(
        repo=FiscalRepository(session),
    ).execute(venda_id=venda_id, empresa_id=empresa_id)


@router.get(
    "/documentos/{doc_id}/status",
    response_model=DocumentoFiscalDTO,
    summary="Status do documento fiscal",
)
async def get_status_documento(
    doc_id: UUID,
    empresa_id: UUID = Depends(get_empresa_id),
    session: AsyncSession = Depends(get_async_session),
    _user=Depends(get_current_user),
) -> DocumentoFiscalDTO:
    return await ConsultarStatusDocumentoUseCase(
        repo=FiscalRepository(session),
    ).execute(doc_id=doc_id, empresa_id=empresa_id)


@router.post(
    "/documentos/{doc_id}/reprocessar",
    response_model=DocumentoFiscalDTO,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Reprocessar documento fiscal rejeitado ou com erro",
)
async def reprocessar_documento(
    doc_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    empresa_id: UUID = Depends(get_empresa_id),
    session: AsyncSession = Depends(get_async_session),
    _user=Depends(get_current_user),
) -> DocumentoFiscalDTO:
    doc = await ReprocessarDocumentoUseCase(
        repo=FiscalRepository(session),
    ).execute(doc_id=doc_id, empresa_id=empresa_id)

    # Enfileira após a sessão fazer commit (BackgroundTasks roda pós-resposta)
    arq_pool = getattr(request.app.state, "arq_pool", None)
    if arq_pool is not None:
        background_tasks.add_task(_enqueue_fiscal_job, arq_pool, str(doc_id))

    return doc
