"""
Modelos: Estoque e MovimentacaoEstoque

Design do sistema de estoque:

  - `Estoque` = saldo atual por produto. Uma linha por produto.
    Atualizado atomicamente em cada MovimentacaoEstoque para garantir
    consistência sem precisar calcular saldo via SUM.

  - `MovimentacaoEstoque` = ledger imutável de todas as entradas e saídas.
    Nunca altere ou delete uma movimentação. Para corrigir, crie um ajuste.

  - O campo `saldo_anterior` e `saldo_posterior` na movimentação permitem
    reconstrução e auditoria sem precisar replay da tabela toda.

  - `referencia_tipo` + `referencia_id` vinculam a movimentação à sua origem
    (venda, compra, ajuste manual, inventário), sem FK hard para múltiplas tabelas.

  - Precisão Numeric(15, 3): suporta até 999.999.999.999,999 unidades.
    3 casas decimais para produtos pesáveis (kg com 3 casas = gramas exatas).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .enums import TipoMovimentacaoEstoque


class LocalEstoque(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Local físico de armazenamento de produtos.

    Permite controle multi-loja e multi-depósito.
    Cada empresa deve ter exatamente um local marcado como `principal`
    (usado como padrão para vendas sem especificação de local).
    """
    __tablename__ = "locais_estoque"
    __table_args__ = (
        UniqueConstraint("empresa_id", "codigo", name="uq_locais_estoque_codigo"),
        # Necessário para FK composta em Estoque(empresa_id, local_estoque_id)
        UniqueConstraint("empresa_id", "id", name="uq_locais_estoque_empresa_id"),
        Index("ix_locais_estoque_empresa_id", "empresa_id"),
        {
            "comment": (
                "Locais físicos de estoque: loja, depósito, filial. "
                "Cada empresa deve ter um local principal."
            )
        },
    )

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    codigo: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Código do local: 'LOJA', 'DEPOSITO', 'FILIAL_SP'",
    )
    descricao: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Ex: Loja Principal, Depósito Fundo, Filial São Paulo",
    )
    principal: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Local principal da empresa — padrão para vendas sem especificação",
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    estoques: Mapped[list["Estoque"]] = relationship(
        "Estoque",
        back_populates="local_estoque",
        lazy="select",
    )


class Estoque(Base, TimestampMixin):
    """
    Saldo atual de estoque por produto POR LOCAL.

    Chave primária composta: (produto_id, local_estoque_id).
    Garante que existe exatamente um saldo por produto/local.

    Controle de concorrência otimista:
        UPDATE estoque
        SET saldo_atual=:novo, versao=versao+1
        WHERE produto_id=:pid AND local_estoque_id=:lid AND versao=:versao_esperada
        → Se affected_rows == 0, outro processo atualizou antes — fazer retry.

    Política de estoque negativo:
        Controlada por `permite_negativo` por local (ex: depósito aceita negativo
        para recebimentos antecipados, loja não).
    """
    __tablename__ = "estoque"
    __table_args__ = (
        # HARDENING: política de negativo explicitada por campo — sem número mágico
        CheckConstraint(
            "saldo_atual >= 0 OR permite_negativo = true",
            name="ck_estoque_saldo_politica_negativo",
        ),
        CheckConstraint("saldo_reservado >= 0", name="ck_estoque_saldo_reservado_positivo"),
        Index("ix_estoque_empresa_id", "empresa_id"),
        Index("ix_estoque_local_id", "local_estoque_id"),
        Index("ix_estoque_saldo_baixo", "empresa_id", "saldo_atual"),
        {"comment": "Saldo atual de estoque por produto e local — atualizado atomicamente"},
    )

    # ---------------------------------------------------------------------------
    # Chave primária composta: produto + local
    # ---------------------------------------------------------------------------
    produto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("produtos.id", ondelete="CASCADE"),
        primary_key=True,
        comment="Componente da PK composta",
    )
    local_estoque_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locais_estoque.id", ondelete="RESTRICT"),
        primary_key=True,
        comment="Componente da PK composta — local físico de armazenamento",
    )
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Desnormalizado para queries por empresa sem JOIN",
    )

    # ---------------------------------------------------------------------------
    # Saldo
    # ---------------------------------------------------------------------------
    saldo_atual: Mapped[float] = mapped_column(
        Numeric(15, 3),
        nullable=False,
        default=0,
        comment="Saldo atual em unidades ou kg.",
    )
    saldo_reservado: Mapped[float] = mapped_column(
        Numeric(15, 3),
        nullable=False,
        default=0,
        comment="Quantidade reservada para vendas em andamento (uso futuro)",
    )

    # ---------------------------------------------------------------------------
    # Política de estoque negativo — explícito por local, não número mágico
    # ---------------------------------------------------------------------------
    permite_negativo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "Permite saldo negativo neste local. "
            "Depósito pode aceitar para recebimentos antecipados; loja geralmente não."
        ),
    )

    # ---------------------------------------------------------------------------
    # Controle de concorrência otimista
    # Incrementar em cada UPDATE: WHERE versao = :esperada → se 0 rows = conflito
    # ---------------------------------------------------------------------------
    versao: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Versão para controle otimista de concorrência. Incrementar em cada UPDATE.",
    )

    # Flag auxiliar para leitura rápida do estoque principal no PDV
    principal: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True = este local é o estoque principal do produto (leitura rápida no PDV)",
    )

    ultima_entrada: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Data/hora da última entrada de estoque",
    )
    ultima_saida: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Data/hora da última saída de estoque",
    )

    # Relationships
    produto: Mapped["Produto"] = relationship(  # noqa: F821
        "Produto",
        back_populates="estoques",
        lazy="select",
    )
    local_estoque: Mapped["LocalEstoque"] = relationship(
        "LocalEstoque",
        back_populates="estoques",
        lazy="select",
    )


class MovimentacaoEstoque(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "movimentacoes_estoque"
    __table_args__ = (
        Index("ix_mov_estoque_produto_id", "produto_id"),
        Index("ix_mov_estoque_empresa_id", "empresa_id"),
        Index("ix_mov_estoque_local_id", "local_estoque_id"),
        Index("ix_mov_estoque_criado_em", "criado_em"),
        # Índice composto para relatórios de movimentação por período e produto
        Index("ix_mov_estoque_produto_data", "produto_id", "criado_em"),
        # Índice para busca por referência (venda_id, compra_id, etc.)
        Index("ix_mov_estoque_referencia", "referencia_tipo", "referencia_id"),
        {"comment": "Ledger imutável de todas as movimentações de estoque"},
    )

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    produto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("produtos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    local_estoque_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locais_estoque.id", ondelete="SET NULL"),
        nullable=True,
        comment="Local físico onde ocorreu a movimentação. NULL = local padrão.",
    )
    usuario_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        comment="Operador responsável. NULL = movimentação automática do sistema.",
    )

    tipo: Mapped[TipoMovimentacaoEstoque] = mapped_column(
        String(35),
        nullable=False,
    )

    # Quantidade — sempre positiva. O tipo determina se é entrada ou saída.
    quantidade: Mapped[float] = mapped_column(
        Numeric(15, 3),
        nullable=False,
        comment="Quantidade movimentada. Sempre positivo — o tipo indica direção.",
    )
    saldo_anterior: Mapped[float] = mapped_column(
        Numeric(15, 3),
        nullable=False,
        comment="Saldo antes da movimentação — snapshot para auditoria",
    )
    saldo_posterior: Mapped[float] = mapped_column(
        Numeric(15, 3),
        nullable=False,
        comment="Saldo após a movimentação — snapshot para auditoria",
    )

    # Custo unitário no momento da movimentação (para custo médio ponderado)
    custo_unitario: Mapped[Optional[float]] = mapped_column(
        Numeric(15, 4),
        comment="Custo unitário do produto no momento da movimentação",
    )

    # Rastreabilidade da origem
    referencia_tipo: Mapped[Optional[str]] = mapped_column(
        String(30),
        comment="Tipo da entidade que originou: 'venda', 'compra', 'ajuste_manual', 'inventario'",
    )
    referencia_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        comment="UUID da entidade de origem. Não é FK para suportar múltiplas origens.",
    )

    motivo: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Justificativa textual para ajustes manuais e inventários",
    )
    documento_fiscal: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="Número/chave do documento fiscal de entrada (NF-e de compra)",
    )

    # Relationships
    produto: Mapped["Produto"] = relationship(  # noqa: F821
        "Produto",
        back_populates="movimentacoes_estoque",
        lazy="select",
    )
    local_estoque: Mapped[Optional["LocalEstoque"]] = relationship(
        "LocalEstoque",
        lazy="select",
    )
    usuario: Mapped[Optional["Usuario"]] = relationship(  # noqa: F821
        "Usuario",
        back_populates="movimentacoes_estoque",
        lazy="select",
    )
