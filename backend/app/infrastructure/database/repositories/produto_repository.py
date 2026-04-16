"""
ProdutoRepository — buscas de produto para o PDV.

Estratégia de busca por EAN:
  1. codigo_barras_principal no próprio Produto (hit mais comum — EAN único)
  2. Tabela produto_eans (EANs alternativos / embalagens)
     Retorna também o fator_quantidade do EAN para que o PDV multiplique
     a quantidade automaticamente (ex: leu DUN-14 de caixa = 12 unidades).
"""
from __future__ import annotations

from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.infrastructure.database.models.produto import Produto, ProdutoEAN
from .base import BaseRepository


class ProdutoRepository(BaseRepository[Produto]):
    def __init__(self, session) -> None:
        super().__init__(Produto, session)

    def _base_query(self):
        return (
            select(Produto)
            .options(
                joinedload(Produto.perfil_tributario),
                joinedload(Produto.unidade),
            )
        )

    async def get_by_id_empresa(
        self, produto_id: UUID, empresa_id: UUID
    ) -> Optional[Produto]:
        """Busca produto ativo por ID, garantindo isolamento de empresa."""
        result = await self._session.execute(
            self._base_query().where(
                Produto.id == produto_id,
                Produto.empresa_id == empresa_id,
                Produto.ativo.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_ean(
        self, ean: str, empresa_id: UUID
    ) -> Optional[Tuple[Produto, float]]:
        """
        Retorna (Produto, fator_quantidade) ou None.

        Busca em dois passos:
          1. codigo_barras_principal — EAN principal do produto
          2. produto_eans — EANs alternativos / embalagens
        """
        # Passo 1: EAN principal
        result = await self._session.execute(
            self._base_query().where(
                Produto.empresa_id == empresa_id,
                Produto.codigo_barras_principal == ean,
                Produto.ativo.is_(True),
            )
        )
        produto = result.scalar_one_or_none()
        if produto:
            return produto, 1.0

        # Passo 2: EAN alternativo
        ean_result = await self._session.execute(
            select(ProdutoEAN).where(
                ProdutoEAN.empresa_id == empresa_id,
                ProdutoEAN.ean == ean,
                ProdutoEAN.ativo.is_(True),
            )
        )
        ean_row = ean_result.scalar_one_or_none()
        if not ean_row:
            return None

        result = await self._session.execute(
            self._base_query().where(
                Produto.id == ean_row.produto_id,
                Produto.ativo.is_(True),
            )
        )
        produto = result.scalar_one_or_none()
        if produto:
            return produto, float(ean_row.fator_quantidade)
        return None
