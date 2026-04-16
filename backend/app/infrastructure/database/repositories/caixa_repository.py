"""
CaixaRepository — gestão de sessões de caixa (turnos).

Nota sobre a unicidade de sessão aberta:
  O banco tem um índice parcial único:
    uq_sessao_caixa_aberta ON sessoes_caixa (caixa_id) WHERE status = 'aberta'
  Isso garante atomicidade na abertura mesmo com múltiplas requisições concorrentes.
  O caso comum (check-before-insert) é suficiente como primeira linha de defesa;
  o índice é a garantia real em cenários de race condition.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.caixa import Caixa, SessaoCaixa
from app.infrastructure.database.models.enums import FormaPagamento, StatusSessaoCaixa, StatusVenda
from app.infrastructure.database.models.venda import PagamentoVenda, Venda
from .base import BaseRepository


class CaixaRepository(BaseRepository[SessaoCaixa]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(SessaoCaixa, session)

    async def get_caixa(self, caixa_id: UUID, empresa_id: UUID) -> Optional[Caixa]:
        result = await self._session.execute(
            select(Caixa).where(
                Caixa.id == caixa_id,
                Caixa.empresa_id == empresa_id,
                Caixa.ativo.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_sessao_ativa(
        self, caixa_id: UUID, empresa_id: UUID
    ) -> Optional[SessaoCaixa]:
        result = await self._session.execute(
            select(SessaoCaixa).where(
                SessaoCaixa.caixa_id == caixa_id,
                SessaoCaixa.empresa_id == empresa_id,
                SessaoCaixa.status == StatusSessaoCaixa.ABERTA,
            )
        )
        return result.scalar_one_or_none()

    async def get_sessao_by_id(
        self, sessao_id: UUID, empresa_id: UUID
    ) -> Optional[SessaoCaixa]:
        result = await self._session.execute(
            select(SessaoCaixa).where(
                SessaoCaixa.id == sessao_id,
                SessaoCaixa.empresa_id == empresa_id,
            )
        )
        return result.scalar_one_or_none()

    async def calcular_totais_sessao(self, sessao_id: UUID) -> dict:
        """Agrega totais das vendas concluídas da sessão para fechamento."""
        venda_result = await self._session.execute(
            select(
                func.count(Venda.id).label("quantidade_vendas"),
                func.coalesce(func.sum(Venda.total_bruto), 0).label("total_vendas_bruto"),
                func.coalesce(func.sum(Venda.total_desconto), 0).label("total_descontos"),
                func.coalesce(func.sum(Venda.total_liquido), 0).label("total_liquido"),
            ).where(
                Venda.sessao_caixa_id == sessao_id,
                Venda.status == StatusVenda.CONCLUIDA,
            )
        )
        pagamento_result = await self._session.execute(
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (PagamentoVenda.forma_pagamento == FormaPagamento.DINHEIRO, PagamentoVenda.valor),
                            else_=0,
                        )
                    ),
                    0,
                ).label("total_dinheiro"),
                func.coalesce(
                    func.sum(
                        case(
                            (PagamentoVenda.forma_pagamento == FormaPagamento.PIX, PagamentoVenda.valor),
                            else_=0,
                        )
                    ),
                    0,
                ).label("total_pix"),
                func.coalesce(
                    func.sum(
                        case(
                            (PagamentoVenda.forma_pagamento == FormaPagamento.CARTAO_DEBITO, PagamentoVenda.valor),
                            else_=0,
                        )
                    ),
                    0,
                ).label("total_cartao_debito"),
                func.coalesce(
                    func.sum(
                        case(
                            (PagamentoVenda.forma_pagamento == FormaPagamento.CARTAO_CREDITO, PagamentoVenda.valor),
                            else_=0,
                        )
                    ),
                    0,
                ).label("total_cartao_credito"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                PagamentoVenda.forma_pagamento.notin_(
                                    [
                                        FormaPagamento.DINHEIRO,
                                        FormaPagamento.PIX,
                                        FormaPagamento.CARTAO_DEBITO,
                                        FormaPagamento.CARTAO_CREDITO,
                                    ]
                                ),
                                PagamentoVenda.valor,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("total_outros"),
            )
            .join(Venda, Venda.id == PagamentoVenda.venda_id)
            .where(
                Venda.sessao_caixa_id == sessao_id,
                Venda.status == StatusVenda.CONCLUIDA,
            )
        )
        row = venda_result.one()
        pagamentos = pagamento_result.one()
        return {
            "quantidade_vendas": int(row.quantidade_vendas or 0),
            "total_vendas_bruto": float(row.total_vendas_bruto or 0),
            "total_descontos": float(row.total_descontos or 0),
            "total_liquido": float(row.total_liquido or 0),
            "total_dinheiro": float(pagamentos.total_dinheiro or 0),
            "total_pix": float(pagamentos.total_pix or 0),
            "total_cartao_debito": float(pagamentos.total_cartao_debito or 0),
            "total_cartao_credito": float(pagamentos.total_cartao_credito or 0),
            "total_outros": float(pagamentos.total_outros or 0),
        }
