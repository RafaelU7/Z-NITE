"""
Router de Produto — GET /v1/produtos/...

Endpoints:
  GET /ean/{ean}         — busca por código de barras (EAN-13/DUN-14/PLU)
  GET /{produto_id}      — busca por UUID
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.produto.dto import ProdutoDTO
from app.application.produto.use_cases import GetProdutoByEANUseCase, GetProdutoByIdUseCase
from app.core.database import get_async_session
from app.core.dependencies import get_empresa_id
from app.infrastructure.database.repositories.produto_repository import ProdutoRepository

router = APIRouter(prefix="/produtos", tags=["Produtos"])


@router.get(
    "/ean/{ean}",
    response_model=ProdutoDTO,
    summary="Buscar produto por EAN / código de barras",
)
async def get_produto_por_ean(
    ean: str,
    empresa_id: UUID = Depends(get_empresa_id),
    session: AsyncSession = Depends(get_async_session),
) -> ProdutoDTO:
    return await GetProdutoByEANUseCase(
        repo=ProdutoRepository(session),
    ).execute(ean=ean, empresa_id=empresa_id)


@router.get(
    "/{produto_id}",
    response_model=ProdutoDTO,
    summary="Buscar produto por ID",
)
async def get_produto_por_id(
    produto_id: UUID,
    empresa_id: UUID = Depends(get_empresa_id),
    session: AsyncSession = Depends(get_async_session),
) -> ProdutoDTO:
    return await GetProdutoByIdUseCase(
        repo=ProdutoRepository(session),
    ).execute(produto_id=produto_id, empresa_id=empresa_id)
