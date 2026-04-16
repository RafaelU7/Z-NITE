"""
Modelos: Caixa, SessaoCaixa, MovimentacaoCaixa

Design do módulo de caixa:

  - `Caixa` = terminal físico (máquina). Pode haver múltiplos caixas na loja.
    Cada caixa tem um número de série que o identifica no ambiente fiscal.

  - `SessaoCaixa` = um turno de trabalho. Um operador abre o caixa com um
    valor de abertura (fundo de troco), opera durante o dia, e fecha ao final
    informando o saldo físico contado. O sistema calcula a diferença (quebra).

  - `MovimentacaoCaixa` = sangrias e suprimentos com rastreabilidade total.
    Sangria = retirada de dinheiro (ex: depositar no cofre).
    Suprimento = colocação de dinheiro (ex: reforçar o troco).

  - Os totais na SessaoCaixa são calculados no fechamento e armazenados
    para performance nos relatórios. A fonte de verdade é sempre a tabela
    de vendas e pagamentos.
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
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .enums import StatusSessaoCaixa, TipoMovimentacaoCaixa


class Caixa(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "caixas"
    __table_args__ = (
        UniqueConstraint("empresa_id", "numero", name="uq_caixas_numero"),
        # Necessário para FK composta em sessoes_caixa(empresa_id, caixa_id)
        UniqueConstraint("empresa_id", "id", name="uq_caixas_empresa_id"),
        Index("ix_caixas_empresa_id", "empresa_id"),
        {"comment": "Terminal de caixa físico — hardware onde roda o PDV"},
    )

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
    )

    numero: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Número sequencial do caixa na loja (1, 2, 3...)",
    )
    descricao: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="Ex: 'Caixa Principal', 'Caixa Rápido'",
    )

    # Número de série do equipamento — necessário para contingência NFC-e
    numero_serie: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Número de série do terminal, exigido por alguns estados para NFC-e",
    )

    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    sessoes: Mapped[list["SessaoCaixa"]] = relationship(
        "SessaoCaixa",
        back_populates="caixa",
        foreign_keys="SessaoCaixa.caixa_id",
        lazy="select",
    )


class SessaoCaixa(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Um turno/sessão de operação do caixa.

    Os campos de totais (total_dinheiro, total_pix, etc.) são
    preenchidos no fechamento da sessão para agilizar relatórios.
    O relatório de conferência pode ser gerado a qualquer momento
    consultando as vendas vinculadas a esta sessão.
    """
    __tablename__ = "sessoes_caixa"
    __table_args__ = (
        Index("ix_sessoes_caixa_caixa_id", "caixa_id"),
        Index("ix_sessoes_caixa_operador_id", "operador_id"),
        Index("ix_sessoes_caixa_status", "empresa_id", "status"),
        Index("ix_sessoes_caixa_abertura", "data_abertura"),
        # HARDENING: Apenas UMA sessão aberta por caixa.
        # Partial unique index: ignora sessões fechadas, bloqueia segunda abertura.
        Index(
            "uq_sessao_caixa_aberta",
            "caixa_id",
            unique=True,
            postgresql_where=text("status = 'aberta'"),
        ),
        # Necessário para FK composta em vendas(empresa_id, sessao_caixa_id)
        UniqueConstraint("empresa_id", "id", name="uq_sessoes_caixa_empresa_id"),
        # HARDENING: FK composta garante que o caixa pertence à mesma empresa.
        # Impede que uma sessão referencie um caixa de outra empresa.
        ForeignKeyConstraint(
            ["empresa_id", "caixa_id"],
            ["caixas.empresa_id", "caixas.id"],
            ondelete="RESTRICT",
            name="fk_sessoes_caixa_empresa_caixa",
        ),
        {"comment": "Sessão/turno de operação do caixa com conferência ao fechamento"},
    )

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    caixa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("caixas.id", ondelete="RESTRICT"),
        nullable=False,
        # FK composta adicional declarada em __table_args__ via ForeignKeyConstraint
        # garante que o caixa pertence à mesma empresa da sessão.
    )
    operador_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Operador que abriu o caixa",
    )
    operador_fechamento_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        comment="Operador que fechou o caixa (pode ser diferente do que abriu)",
    )

    status: Mapped[StatusSessaoCaixa] = mapped_column(
        String(10),
        nullable=False,
        default=StatusSessaoCaixa.ABERTA,
    )

    # Timestamps da sessão
    data_abertura: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    data_fechamento: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
    )

    # Conferência de caixa
    saldo_abertura: Mapped[float] = mapped_column(
        Numeric(15, 4),
        nullable=False,
        default=0,
        comment="Valor em dinheiro colocado no caixa na abertura (fundo de troco)",
    )
    saldo_informado_fechamento: Mapped[Optional[float]] = mapped_column(
        Numeric(15, 4),
        comment="Valor que o operador diz ter no caixa ao fechar (contagem física)",
    )
    saldo_sistema_fechamento: Mapped[Optional[float]] = mapped_column(
        Numeric(15, 4),
        comment="Valor esperado pelo sistema: abertura + entradas - saídas em dinheiro",
    )
    diferenca_fechamento: Mapped[Optional[float]] = mapped_column(
        Numeric(15, 4),
        comment="Quebra: saldo_informado - saldo_sistema. Negativo = falta.",
    )

    # Totais calculados no fechamento (snapshot para performance)
    total_vendas_bruto: Mapped[Optional[float]] = mapped_column(Numeric(15, 4))
    total_cancelamentos: Mapped[Optional[float]] = mapped_column(Numeric(15, 4))
    total_descontos: Mapped[Optional[float]] = mapped_column(Numeric(15, 4))
    total_liquido: Mapped[Optional[float]] = mapped_column(Numeric(15, 4))
    total_sangrias: Mapped[Optional[float]] = mapped_column(Numeric(15, 4))
    total_suprimentos: Mapped[Optional[float]] = mapped_column(Numeric(15, 4))

    # Totais por forma de pagamento (snapshot)
    total_dinheiro: Mapped[Optional[float]] = mapped_column(Numeric(15, 4))
    total_pix: Mapped[Optional[float]] = mapped_column(Numeric(15, 4))
    total_cartao_debito: Mapped[Optional[float]] = mapped_column(Numeric(15, 4))
    total_cartao_credito: Mapped[Optional[float]] = mapped_column(Numeric(15, 4))
    total_outros: Mapped[Optional[float]] = mapped_column(Numeric(15, 4))

    quantidade_vendas: Mapped[Optional[int]] = mapped_column(Integer)
    ticket_medio: Mapped[Optional[float]] = mapped_column(Numeric(15, 4))

    observacao_fechamento: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    caixa: Mapped["Caixa"] = relationship(
        "Caixa",
        back_populates="sessoes",
        foreign_keys=[caixa_id],
        lazy="select",
    )
    operador: Mapped["Usuario"] = relationship(  # noqa: F821
        "Usuario",
        back_populates="sessoes_caixa",
        foreign_keys=[operador_id],
        lazy="select",
    )
    movimentacoes: Mapped[list["MovimentacaoCaixa"]] = relationship(
        "MovimentacaoCaixa",
        back_populates="sessao",
        foreign_keys="MovimentacaoCaixa.sessao_id",
        lazy="select",
        cascade="all, delete-orphan",
    )
    vendas: Mapped[list["Venda"]] = relationship(  # noqa: F821
        "Venda",
        back_populates="sessao_caixa",
        foreign_keys="Venda.sessao_caixa_id",
        lazy="select",
    )


class MovimentacaoCaixa(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Sangrias e suprimentos — movimentações manuais de dinheiro no caixa."""
    __tablename__ = "movimentacoes_caixa"
    __table_args__ = (
        Index("ix_mov_caixa_sessao_id", "sessao_id"),
        Index("ix_mov_caixa_criado_em", "criado_em"),
        CheckConstraint("valor > 0", name="ck_mov_caixa_valor_positivo"),        # HARDENING: FK composta garante que a movimentação pertence à sessão
        # da mesma empresa — impede movimentações cruzando empresas.
        ForeignKeyConstraint(
            ["empresa_id", "sessao_id"],
            ["sessoes_caixa.empresa_id", "sessoes_caixa.id"],
            ondelete="RESTRICT",
            name="fk_mov_caixa_empresa_sessao",
        ),        {"comment": "Sangrias e suprimentos rastreáveis por operador"},
    )

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sessao_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessoes_caixa.id", ondelete="RESTRICT"),
        nullable=False,
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Operador que realizou a sangria/suprimento",
    )
    autorizado_por_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        comment="Gerente/supervisor que autorizou (para sangrias acima de limites)",
    )

    tipo: Mapped[TipoMovimentacaoCaixa] = mapped_column(String(15), nullable=False)
    valor: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False)
    motivo: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    sessao: Mapped["SessaoCaixa"] = relationship(
        "SessaoCaixa",
        back_populates="movimentacoes",
        foreign_keys=[sessao_id],
        lazy="select",
    )
