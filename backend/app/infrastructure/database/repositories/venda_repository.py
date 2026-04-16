"""
VendaRepository — operações de persistência do ciclo de vida de uma venda.

Responsabilidades:
  - Lookup de venda com eager-load de itens e pagamentos
  - Verificação de idempotência via chave_idempotencia
  - Geração de numero_venda_local (MAX dentro da sessão + 1)
  - Consulta e criação de ItemVenda e PagamentoVenda
  - Recálculo de totais após mutação de itens

Nota sobre eager-load:
  Usamos joinedload + .unique() para obter os relacionamentos em
  uma única query e desduplicar linhas resultantes do JOIN.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.infrastructure.database.models.venda import ItemVenda, Venda
from .base import BaseRepository


class VendaRepository(BaseRepository[Venda]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Venda, session)

    async def get_by_id_empresa(
        self, venda_id: UUID, empresa_id: UUID
    ) -> Optional[Venda]:
        """Carrega a venda com itens e pagamentos em uma query (joinedload)."""
        result = await self._session.execute(
            select(Venda)
            .options(
                joinedload(Venda.itens),
                joinedload(Venda.pagamentos),
            )
            .execution_options(populate_existing=True)
            .where(
                Venda.id == venda_id,
                Venda.empresa_id == empresa_id,
            )
        )
        return result.unique().scalar_one_or_none()

    async def get_by_idempotencia(
        self, chave: UUID, empresa_id: UUID
    ) -> Optional[Venda]:
        result = await self._session.execute(
            select(Venda)
            .options(
                joinedload(Venda.itens),
                joinedload(Venda.pagamentos),
            )
            .execution_options(populate_existing=True)
            .where(
                Venda.chave_idempotencia == chave,
                Venda.empresa_id == empresa_id,
            )
        )
        return result.unique().scalar_one_or_none()

    async def proximo_numero_local(self, sessao_caixa_id: UUID) -> int:
        result = await self._session.execute(
            select(func.coalesce(func.max(Venda.numero_venda_local), 0)).where(
                Venda.sessao_caixa_id == sessao_caixa_id
            )
        )
        return int(result.scalar()) + 1

    async def get_item(
        self, item_id: UUID, venda_id: UUID
    ) -> Optional[ItemVenda]:
        """Retorna item ativo (não cancelado) pelo ID."""
        result = await self._session.execute(
            select(ItemVenda).where(
                ItemVenda.id == item_id,
                ItemVenda.venda_id == venda_id,
                ItemVenda.cancelado.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def proximo_sequencial_item(self, venda_id: UUID) -> int:
        result = await self._session.execute(
            select(func.coalesce(func.max(ItemVenda.sequencia), 0)).where(
                ItemVenda.venda_id == venda_id,
                ItemVenda.cancelado.is_(False),
            )
        )
        return int(result.scalar()) + 1

    async def atualizar_totais(self, venda: Venda) -> None:
        """
        Recalcula total_bruto, total_desconto e total_liquido da venda
        somando apenas os itens não cancelados.
        """
        result = await self._session.execute(
            select(
                func.coalesce(
                    func.sum(ItemVenda.preco_unitario * ItemVenda.quantidade), 0
                ).label("total_bruto"),
                func.coalesce(
                    func.sum(ItemVenda.desconto_unitario * ItemVenda.quantidade), 0
                ).label("total_desconto"),
                func.coalesce(func.sum(ItemVenda.total_item), 0).label("total_liquido"),
            ).where(
                ItemVenda.venda_id == venda.id,
                ItemVenda.cancelado.is_(False),
            )
        )
        row = result.one()
        venda.total_bruto = float(row.total_bruto)
        venda.total_desconto = float(row.total_desconto)
        venda.total_liquido = float(row.total_liquido)
        await self._session.flush()
