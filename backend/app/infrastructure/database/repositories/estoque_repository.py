"""
EstoqueRepository — controle de saldo com SELECT FOR UPDATE.

Estratégia de concorrência:
  Para decréscimos (vendas) e acréscimos (cancelamentos), usamos SELECT FOR UPDATE
  para evitar que dois PDVs simultâneos leiam o mesmo saldo e gerem saldo negativo.

  A política de negativo é por local (permite_negativo):
    - Se False e novo_saldo < 0 → BusinessRuleError
    - Se True → permite (útil para depósito com recebimentos antecipados)

  O campo `versao` é incrementado em cada UPDATE como registro de auditoria;
  não usamos comparação optimista (WHERE versao = :esperada) porque o FOR UPDATE
  já serializa os acessos concorrentes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError
from app.infrastructure.database.models.estoque import (
    Estoque,
    LocalEstoque,
    MovimentacaoEstoque,
)
from app.infrastructure.database.models.enums import TipoMovimentacaoEstoque
from .base import BaseRepository


class EstoqueRepository(BaseRepository[Estoque]):
    """
    BaseRepository<Estoque> herdado por compatibilidade.
    get_by_id() não é usada aqui (PK composta).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Estoque, session)

    async def _find_local_principal_id(
        self, produto_id: UUID, empresa_id: UUID
    ) -> Optional[UUID]:
        """Retorna local_estoque_id do local principal ativo."""
        result = await self._session.execute(
            select(Estoque.local_estoque_id)
            .join(LocalEstoque, LocalEstoque.id == Estoque.local_estoque_id)
            .where(
                Estoque.produto_id == produto_id,
                Estoque.empresa_id == empresa_id,
                LocalEstoque.principal.is_(True),
                LocalEstoque.ativo.is_(True),
            )
        )
        row = result.first()
        return row[0] if row else None

    async def _get_for_update(
        self, produto_id: UUID, local_estoque_id: UUID
    ) -> Optional[Estoque]:
        result = await self._session.execute(
            select(Estoque)
            .where(
                Estoque.produto_id == produto_id,
                Estoque.local_estoque_id == local_estoque_id,
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_estoque_principal(
        self, produto_id: UUID, empresa_id: UUID
    ) -> Optional[Estoque]:
        """Leitura simples do estoque principal (sem lock)."""
        local_id = await self._find_local_principal_id(produto_id, empresa_id)
        if not local_id:
            return None
        result = await self._session.execute(
            select(Estoque).where(
                Estoque.produto_id == produto_id,
                Estoque.local_estoque_id == local_id,
            )
        )
        return result.scalar_one_or_none()

    async def reduzir_saldo_principal(
        self,
        produto_id: UUID,
        empresa_id: UUID,
        quantidade: float,
    ) -> Optional[Estoque]:
        """
        Reduz o saldo do local principal com SELECT FOR UPDATE.
        Retorna o Estoque atualizado, ou None se não existir registro.
        Levanta BusinessRuleError se o saldo ficaria negativo e permite_negativo=False.
        """
        local_id = await self._find_local_principal_id(produto_id, empresa_id)
        if not local_id:
            return None

        estoque = await self._get_for_update(produto_id, local_id)
        if not estoque:
            return None

        novo_saldo = float(estoque.saldo_atual) - quantidade
        if novo_saldo < 0 and not estoque.permite_negativo:
            raise BusinessRuleError(
                f"Estoque insuficiente. Saldo atual: {float(estoque.saldo_atual):.3f}, "
                f"quantidade solicitada: {quantidade:.3f}."
            )

        estoque.saldo_atual = novo_saldo
        estoque.versao += 1
        estoque.ultima_saida = datetime.now(timezone.utc)
        await self._session.flush()
        return estoque

    async def aumentar_saldo_principal(
        self,
        produto_id: UUID,
        empresa_id: UUID,
        quantidade: float,
    ) -> Optional[Estoque]:
        """Restaura saldo (ex: cancelamento de item) com SELECT FOR UPDATE."""
        local_id = await self._find_local_principal_id(produto_id, empresa_id)
        if not local_id:
            return None

        estoque = await self._get_for_update(produto_id, local_id)
        if not estoque:
            return None

        estoque.saldo_atual = float(estoque.saldo_atual) + quantidade
        estoque.versao += 1
        await self._session.flush()
        return estoque

    async def criar_movimentacao(
        self,
        empresa_id: UUID,
        produto_id: UUID,
        local_estoque_id: UUID,
        usuario_id: Optional[UUID],
        tipo: TipoMovimentacaoEstoque,
        quantidade: float,
        saldo_anterior: float,
        saldo_posterior: float,
        custo_unitario: Optional[float],
        referencia_tipo: Optional[str],
        referencia_id: Optional[UUID],
        motivo: Optional[str] = None,
    ) -> MovimentacaoEstoque:
        """Insere um lançamento imutável no ledger de movimentações."""
        mov = MovimentacaoEstoque(
            empresa_id=empresa_id,
            produto_id=produto_id,
            local_estoque_id=local_estoque_id,
            usuario_id=usuario_id,
            tipo=tipo,
            quantidade=quantidade,
            saldo_anterior=saldo_anterior,
            saldo_posterior=saldo_posterior,
            custo_unitario=custo_unitario,
            referencia_tipo=referencia_tipo,
            referencia_id=referencia_id,
            motivo=motivo,
        )
        self._session.add(mov)
        await self._session.flush()
        return mov
