"""
Modelos: Venda, ItemVenda, PagamentoVenda

Este é o núcleo operacional do sistema. Decisões arquiteturais críticas:

OFFLINE-FIRST:
  - O UUID da venda é gerado no cliente (React/PDV), não no servidor.
    Isso permite criar a venda offline e sincronizar depois sem conflito.
  - `sincronizada` + `data_sinc` controlam o estado de sincronização.
  - `numero_venda_local` é o número sequencial do PDV (exibido ao operador).
  - A integridade é garantida pelo UUID, não pelo número sequencial.

SNAPSHOT FISCAL (ItemVenda):
  - Cada item armazena um snapshot JSONB de todos os dados fiscais no
    momento da venda. Isso é essencial porque:
    (a) o perfil tributário pode mudar depois da venda
    (b) a SEFAZ exige os dados do momento da emissão
    (c) auditoria fiscal requer imutabilidade histórica
  - Os campos individuais (ncm, cfop, csosn, etc.) são armazenados também
    como colunas separadas para facilitar queries e relatórios sem parsear JSONB.

IMUTABILIDADE:
  - Vendas concluídas não devem ser alteradas, apenas canceladas.
  - Cancelamento de item individual é possível com rastreabilidade.
  - Cancelamento total da venda exige operador com permissão.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .enums import FormaPagamento, StatusVenda, TipoEmissao


class Venda(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "vendas"
    __table_args__ = (
        Index("ix_vendas_empresa_id", "empresa_id"),
        Index("ix_vendas_sessao_caixa_id", "sessao_caixa_id"),
        Index("ix_vendas_operador_id", "operador_id"),
        # Índice para relatórios por data — crítico para performance
        Index("ix_vendas_data_venda", "empresa_id", "data_venda"),
        Index("ix_vendas_status", "empresa_id", "status"),
        # HARDENING: unicidade de número local por sessão — substitui o simples Index
        # Garante idempotência na sincronização: mesmo num_local + sessão = mesma venda
        UniqueConstraint(
            "sessao_caixa_id", "numero_venda_local",
            name="uq_vendas_numero_local_por_sessao",
        ),
        # Necessário para FK composta em itens_venda e documentos_fiscais
        UniqueConstraint("empresa_id", "id", name="uq_vendas_empresa_id"),
        CheckConstraint("total_liquido >= 0", name="ck_vendas_total_positivo"),
        # HARDENING: FK composta garante que a sessão pertence à mesma empresa.
        # Impede venda de empresa A referenciar sessão de empresa B.
        ForeignKeyConstraint(
            ["empresa_id", "sessao_caixa_id"],
            ["sessoes_caixa.empresa_id", "sessoes_caixa.id"],
            ondelete="RESTRICT",
            name="fk_vendas_empresa_sessao_caixa",
        ),
        {"comment": "Registro de vendas — suporte offline-first com UUID gerado no cliente"},
    )

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sessao_caixa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessoes_caixa.id", ondelete="RESTRICT"),
        nullable=False,
    )
    operador_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # ---------------------------------------------------------------------------
    # Identificação e rastreabilidade
    # ---------------------------------------------------------------------------
    numero_venda_local: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Número sequencial da venda no turno — gerado no PDV, exibido no recibo",
    )
    status: Mapped[StatusVenda] = mapped_column(
        String(15),
        nullable=False,
        default=StatusVenda.EM_ABERTO,
    )
    tipo_emissao: Mapped[TipoEmissao] = mapped_column(
        SqlEnum(TipoEmissao, name="tipo_emissao_enum", create_type=True),
        nullable=False,
        default=TipoEmissao.FISCAL,
        server_default="FISCAL",
        comment="FISCAL = emite NFC-e; GERENCIAL = registra sem documento fiscal",
    )

    # ---------------------------------------------------------------------------
    # Timestamps — distinção importante entre hora da venda e hora do registro
    # ---------------------------------------------------------------------------
    data_venda: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Data/hora da venda conforme relógio do PDV (pode ser offline)",
    )
    # `criado_em` (do TimestampMixin) = data/hora do registro no servidor

    # ---------------------------------------------------------------------------
    # Valores
    # ---------------------------------------------------------------------------
    total_bruto: Mapped[float] = mapped_column(
        Numeric(15, 4),
        nullable=False,
        default=0,
        comment="Soma dos subtotais dos itens sem descontos",
    )
    total_desconto: Mapped[float] = mapped_column(
        Numeric(15, 4),
        nullable=False,
        default=0,
        comment="Total de descontos aplicados",
    )
    total_liquido: Mapped[float] = mapped_column(
        Numeric(15, 4),
        nullable=False,
        default=0,
        comment="Valor final da venda: total_bruto - total_desconto",
    )
    total_custo: Mapped[Optional[float]] = mapped_column(
        Numeric(15, 4),
        comment="Custo total dos produtos vendidos — para cálculo de margem",
    )

    # ---------------------------------------------------------------------------
    # Cancelamento
    # ---------------------------------------------------------------------------
    cancelada_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancelada_por_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    motivo_cancelamento: Mapped[Optional[str]] = mapped_column(Text)

    # ---------------------------------------------------------------------------
    # Offline-first
    # ---------------------------------------------------------------------------
    sincronizada: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="False = venda criada offline, ainda não confirmada pelo servidor",
    )
    data_sinc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Data/hora em que a venda offline foi sincronizada",
    )
    origem_pdv: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Identificador do terminal PDV de origem (para raástreio offline)",
    )
    # HARDENING: chave de idempotência para sincronização offline.
    # O PDV gera este UUID antes de enviar ao servidor. O servidor rejeita
    # (409 Conflict) qualquer segunda requisição com a mesma chave.
    chave_idempotencia: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        comment=(
            "UUID gerado pelo PDV para garantir idempotência na sincronização. "
            "Impede duplicação de venda offline mesmo em retry."
        ),
    )

    # Relationships
    sessao_caixa: Mapped["SessaoCaixa"] = relationship(  # noqa: F821
        "SessaoCaixa",
        back_populates="vendas",
        foreign_keys=[sessao_caixa_id],
        lazy="select",
    )
    operador: Mapped["Usuario"] = relationship(  # noqa: F821
        "Usuario",
        back_populates="vendas",
        foreign_keys=[operador_id],
        lazy="select",
    )
    itens: Mapped[list["ItemVenda"]] = relationship(
        "ItemVenda",
        back_populates="venda",
        foreign_keys="ItemVenda.venda_id",
        lazy="select",
        cascade="all, delete-orphan",
    )
    pagamentos: Mapped[list["PagamentoVenda"]] = relationship(
        "PagamentoVenda",
        back_populates="venda",
        foreign_keys="PagamentoVenda.venda_id",
        lazy="select",
        cascade="all, delete-orphan",
    )
    documento_fiscal: Mapped[Optional["DocumentoFiscal"]] = relationship(  # noqa: F821
        "DocumentoFiscal",
        back_populates="venda",
        foreign_keys="DocumentoFiscal.venda_id",
        uselist=False,
        lazy="select",
    )


class ItemVenda(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Item de uma venda com snapshot completo dos dados no momento da venda.

    O snapshot_fiscal (JSONB) armazena o PerfilTributario inteiro no
    momento da emissão. Os campos individuais de fiscalidade são armazenados
    também como colunas para facilitar queries SQL e relatórios.
    """
    __tablename__ = "itens_venda"
    __table_args__ = (
        Index("ix_itens_venda_venda_id", "venda_id"),
        Index("ix_itens_venda_produto_id", "produto_id"),
        # Índice para relatórios de produtos mais vendidos
        Index("ix_itens_venda_produto_data", "produto_id", "criado_em"),        # HARDENING: FK composta garante que o item pertence à venda da mesma empresa.
        ForeignKeyConstraint(
            ["empresa_id", "venda_id"],
            ["vendas.empresa_id", "vendas.id"],
            ondelete="CASCADE",
            name="fk_itens_venda_empresa_venda",
        ),
        # HARDENING: Impede item sem nenhum dado fiscal.
        # O item deve ter o snapshot completo (JSONB) OU os campos mínimos individuais.
        # Campos mínimos para NFC-e: NCM + CFOP + CST PIS + CST COFINS
        # + (CSOSN para SN ou CST_ICMS para LP/LR).
        CheckConstraint(
            "snapshot_fiscal IS NOT NULL OR ("
            "ncm IS NOT NULL AND cfop IS NOT NULL AND "
            "cst_pis IS NOT NULL AND cst_cofins IS NOT NULL AND "
            "(csosn IS NOT NULL OR cst_icms IS NOT NULL)"
            ")",
            name="ck_item_venda_fiscal_minimo",
        ),        {"comment": "Itens de venda com snapshot fiscal imutável"},
    )

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    venda_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendas.id", ondelete="CASCADE"),
        nullable=False,
    )
    produto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("produtos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # FK histórica para o perfil tributário vigente no momento da venda
    perfil_tributario_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("perfis_tributarios.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ---------------------------------------------------------------------------
    # Snapshot do produto no momento da venda (imutável)
    # Necessário para que alterações futuras no produto não afetem histórico.
    # ---------------------------------------------------------------------------
    descricao_produto: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Snapshot da descrição do produto no momento da venda",
    )
    codigo_barras: Mapped[Optional[str]] = mapped_column(
        String(14),
        comment="Snapshot do EAN usado para bipar o produto",
    )
    unidade: Mapped[Optional[str]] = mapped_column(
        String(6),
        comment="Snapshot do código da unidade de medida",
    )

    # ---------------------------------------------------------------------------
    # Valores
    # ---------------------------------------------------------------------------
    sequencia: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Ordem dos itens na venda (começa em 1)",
    )
    quantidade: Mapped[float] = mapped_column(
        Numeric(15, 3),
        nullable=False,
        comment="Quantidade com 3 casas para produtos pesáveis",
    )
    preco_unitario: Mapped[float] = mapped_column(
        Numeric(15, 4),
        nullable=False,
        comment="Preço unitário no momento da venda (snapshot)",
    )
    custo_unitario: Mapped[Optional[float]] = mapped_column(
        Numeric(15, 4),
        comment="Custo médio no momento da venda (para margem histórica)",
    )
    desconto_unitario: Mapped[float] = mapped_column(
        Numeric(15, 4),
        nullable=False,
        default=0,
    )
    total_item: Mapped[float] = mapped_column(
        Numeric(15, 4),
        nullable=False,
        comment="(preco_unitario - desconto_unitario) * quantidade",
    )

    # ---------------------------------------------------------------------------
    # Snapshot fiscal — campos individuais para queries + JSONB completo
    # ---------------------------------------------------------------------------
    ncm: Mapped[Optional[str]] = mapped_column(
        String(8),
        comment="NCM snapshot — obrigatório na NF-e",
    )
    cest: Mapped[Optional[str]] = mapped_column(String(7))
    cfop: Mapped[Optional[str]] = mapped_column(
        String(4),
        comment="CFOP vigente para a operação no momento da venda",
    )
    origem: Mapped[Optional[str]] = mapped_column(String(1))
    csosn: Mapped[Optional[str]] = mapped_column(
        String(3),
        comment="CSOSN (Simples Nacional)",
    )
    cst_icms: Mapped[Optional[str]] = mapped_column(
        String(3),
        comment="CST ICMS (Lucro Presumido/Real)",
    )
    aliq_icms: Mapped[Optional[float]] = mapped_column(Numeric(7, 4))
    cst_pis: Mapped[Optional[str]] = mapped_column(String(2))
    aliq_pis: Mapped[Optional[float]] = mapped_column(Numeric(7, 4))
    cst_cofins: Mapped[Optional[str]] = mapped_column(String(2))
    aliq_cofins: Mapped[Optional[float]] = mapped_column(Numeric(7, 4))

    # JSONB completo do perfil tributário no momento da venda
    # Camada de segurança adicional — fonte final de verdade fiscal
    snapshot_fiscal: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        comment="Snapshot completo do PerfilTributario no momento da venda",
    )

    # ---------------------------------------------------------------------------
    # Cancelamento de item individual
    # ---------------------------------------------------------------------------
    cancelado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cancelado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancelado_por_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    venda: Mapped["Venda"] = relationship(
        "Venda",
        back_populates="itens",
        foreign_keys=[venda_id],
        lazy="select",
    )
    produto: Mapped["Produto"] = relationship(  # noqa: F821
        "Produto",
        back_populates="itens_venda",
        lazy="select",
    )
    perfil_tributario_historico: Mapped[Optional["PerfilTributario"]] = relationship(  # noqa: F821
        "PerfilTributario",
        back_populates="itens_venda",
        lazy="select",
    )


class PagamentoVenda(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Pagamentos de uma venda. Uma venda pode ter múltiplas formas de pagamento
    (ex: R$50 em dinheiro + R$30 no cartão de débito).
    """
    __tablename__ = "pagamentos_venda"
    __table_args__ = (
        Index("ix_pagamentos_venda_venda_id", "venda_id"),
        Index("ix_pagamentos_venda_forma", "empresa_id", "forma_pagamento"),
        CheckConstraint("valor > 0", name="ck_pagamentos_valor_positivo"),
        # HARDENING: FK composta garante que o pagamento pertence à venda da mesma empresa.
        ForeignKeyConstraint(
            ["empresa_id", "venda_id"],
            ["vendas.empresa_id", "vendas.id"],
            ondelete="CASCADE",
            name="fk_pagamentos_empresa_venda",
        ),
        {"comment": "Formas de pagamento aplicadas a uma venda (suporte a pagamento misto)"},
    )

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    venda_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendas.id", ondelete="CASCADE"),
        nullable=False,
    )

    forma_pagamento: Mapped[FormaPagamento] = mapped_column(
        String(2),
        nullable=False,
    )
    valor: Mapped[float] = mapped_column(
        Numeric(15, 4),
        nullable=False,
        comment="Valor pago nesta forma de pagamento",
    )
    troco: Mapped[float] = mapped_column(
        Numeric(15, 4),
        nullable=False,
        default=0,
        comment="Troco devolvido (apenas dinheiro)",
    )

    # Dados de cartão (quando aplicável)
    nsu: Mapped[Optional[str]] = mapped_column(
        String(20),
        comment="Número Sequencial Único da transação de cartão",
    )
    bandeira_cartao: Mapped[Optional[str]] = mapped_column(
        String(30),
        comment="Ex: Visa, Mastercard, Elo, Pix",
    )
    autorizacao_cartao: Mapped[Optional[str]] = mapped_column(
        String(20),
        comment="Código de autorização da operadora de cartão",
    )

    # Relationships
    venda: Mapped["Venda"] = relationship(
        "Venda",
        back_populates="pagamentos",
        foreign_keys=[venda_id],
        lazy="select",
    )
