"""
Modelo: Perfil Tributário (Versionado)

O coração fiscal do produto. Centraliza todos os dados tributários necessários
para geração de NF-e / NFC-e conforme o Manual de Orientação do Contribuinte
da SEFAZ e o layout 4.0.

Decisão arquitetural — Versionamento:
  - Nunca sobrescreva um perfil fiscal ativo. Crie uma nova versão.
  - O campo `ativo` indica o perfil em vigência para novos documentos.
  - O campo `vigencia_inicio` / `vigencia_fim` permite consultar qual perfil
    estava ativo em qualquer data passada (fundamental para auditoria fiscal).
  - `ItemVenda` armazena um snapshot JSONB do perfil no momento da venda,
    como camada adicional de imutabilidade histórica.

Campos suportados:
  - NCM (obrigatório por lei)
  - CEST (obrigatório quando há Substituição Tributária)
  - CFOP separado para operações internas e interestaduais
  - CST_ICMS (Lucro Presumido / Real) ou CSOSN (Simples Nacional)
  - PIS e COFINS com CST e alíquotas
  - IPI para produtos industrializados (opcional)
  - ICMS-ST quando aplicável
  - Unidade tributável e fator de conversão quando diferem da unidade comercial
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .enums import ModalidadeBCICMS, ModalidadeBCICMSST, OrigemMercadoria


class PerfilTributario(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Configuração fiscal de um produto em um determinado período de vigência.

    Cada produto aponta para o perfil ativo. Ao alterar regras fiscais,
    fecha-se a versão atual (vigencia_fim) e cria-se uma nova com ativo=True.
    """
    __tablename__ = "perfis_tributarios"
    __table_args__ = (
        Index("ix_perfil_trib_empresa_ativo", "empresa_id", "ativo"),
        Index("ix_perfil_trib_ncm", "ncm"),
        # ---------------------------------------------------------------------------
        # HARDENING: Apenas um perfil com o mesmo nome pode estar ativo por empresa.
        # Partial unique index garante isso sem bloquear histórico inativo.
        # ---------------------------------------------------------------------------
        Index(
            "uq_perfil_tributario_nome_ativo",
            "empresa_id", "nome",
            unique=True,
            postgresql_where=text("ativo = true"),
        ),
        # HARDENING: Impede coexistência de CSOSN (Simples) e CST_ICMS (LP/LR) no
        # mesmo perfil. São mutuamente exclusivos pelo regime tributário.
        CheckConstraint(
            "(csosn IS NULL) OR (cst_icms IS NULL)",
            name="ck_perfil_trib_icms_exclusivo",
        ),
        # HARDENING: Vigência fim deve ser posterior à vigência início.
        CheckConstraint(
            "vigencia_fim IS NULL OR vigencia_fim > vigencia_inicio",
            name="ck_perfil_trib_vigencia_valida",
        ),
        # HARDENING: Perfil ativo não pode ter vigencia_fim no passado.
        # (Impede criação de perfil ativo já expirado.)
        CheckConstraint(
            "ativo = false OR vigencia_fim IS NULL",
            name="ck_perfil_trib_ativo_sem_fim",
        ),
        {"comment": "Perfis fiscais versionados por produto"},
    )

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Identificação do perfil
    nome: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        comment="Nome descritivo do perfil, ex: 'Alimentos - Simples Nacional'",
    )
    descricao: Mapped[Optional[str]] = mapped_column(Text)

    # Versionamento temporal
    ativo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Apenas um perfil com o mesmo nome deve estar ativo por vez",
    )
    vigencia_inicio: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Data de início de vigência deste perfil",
    )
    vigencia_fim: Mapped[Optional[date]] = mapped_column(
        Date,
        comment="Data de fim de vigência. NULL = ainda vigente.",
    )

    # ---------------------------------------------------------------------------
    # Classificação fiscal — campos obrigatórios na NF-e
    # ---------------------------------------------------------------------------
    ncm: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        comment="Nomenclatura Comum do Mercosul — 8 dígitos obrigatórios",
    )
    cest: Mapped[Optional[str]] = mapped_column(
        String(7),
        comment="Código de Especificação da Substituição Tributária. Obrigatório quando há ST.",
    )

    origem: Mapped[OrigemMercadoria] = mapped_column(
        String(1),
        nullable=False,
        default=OrigemMercadoria.NACIONAL,
        comment="Origem da mercadoria conforme tabela de origem do MOC",
    )

    # CFOP — separado por escopo para flexibilidade
    cfop_saida_interna: Mapped[str] = mapped_column(
        String(4),
        nullable=False,
        comment="CFOP para vendas dentro do estado — geralmente 5102, 5405",
    )
    cfop_saida_interestadual: Mapped[Optional[str]] = mapped_column(
        String(4),
        comment="CFOP para vendas para outros estados — geralmente 6102, 6404",
    )

    # ---------------------------------------------------------------------------
    # ICMS — Simples Nacional (CSOSN)
    # Usar quando empresa.regime_tributario IN ('SN', 'SNE')
    # ---------------------------------------------------------------------------
    csosn: Mapped[Optional[str]] = mapped_column(
        String(3),
        comment=(
            "Código Situação da Operação Simples Nacional. "
            "Valores: 101,102,103,201,202,203,300,400,500,900"
        ),
    )

    # ---------------------------------------------------------------------------
    # ICMS — Lucro Presumido / Real (CST)
    # Usar quando empresa.regime_tributario IN ('LP', 'LR')
    # ---------------------------------------------------------------------------
    cst_icms: Mapped[Optional[str]] = mapped_column(
        String(3),
        comment="CST ICMS: 00,10,20,30,40,41,50,51,60,70,90",
    )
    modalidade_bc_icms: Mapped[Optional[ModalidadeBCICMS]] = mapped_column(
        String(1),
        comment="Modalidade de determinação da BC do ICMS",
    )
    aliq_icms: Mapped[Optional[float]] = mapped_column(
        Numeric(7, 4),
        comment="Alíquota ICMS em percentual, ex: 12.0000",
    )
    reducao_bc_icms: Mapped[Optional[float]] = mapped_column(
        Numeric(7, 4),
        comment="Percentual de redução da base de cálculo do ICMS",
    )

    # ICMS Substituição Tributária
    modalidade_bc_icms_st: Mapped[Optional[ModalidadeBCICMSST]] = mapped_column(
        String(1),
    )
    margem_valor_agregado_icms_st: Mapped[Optional[float]] = mapped_column(
        Numeric(7, 4),
        comment="MVA — Margem de Valor Agregado para ICMS-ST em percentual",
    )
    reducao_bc_icms_st: Mapped[Optional[float]] = mapped_column(Numeric(7, 4))
    aliq_icms_st: Mapped[Optional[float]] = mapped_column(Numeric(7, 4))

    # Código de benefício fiscal (ex: isenções, imunidades)
    codigo_beneficio_fiscal: Mapped[Optional[str]] = mapped_column(
        String(10),
        comment="Código de benefício fiscal estadual, quando aplicável",
    )

    # ---------------------------------------------------------------------------
    # PIS
    # ---------------------------------------------------------------------------
    cst_pis: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        comment="CST PIS: 01,02,04,05,06,07,08,49,50,51,99",
    )
    aliq_pis: Mapped[float] = mapped_column(
        Numeric(7, 4),
        nullable=False,
        default=0,
        comment="Alíquota PIS em percentual. 0 quando isento/não tributado.",
    )

    # ---------------------------------------------------------------------------
    # COFINS
    # ---------------------------------------------------------------------------
    cst_cofins: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        comment="CST COFINS — mesmos valores do CST PIS",
    )
    aliq_cofins: Mapped[float] = mapped_column(
        Numeric(7, 4),
        nullable=False,
        default=0,
        comment="Alíquota COFINS em percentual",
    )

    # ---------------------------------------------------------------------------
    # IPI (Imposto sobre Produtos Industrializados)
    # Apenas para produtos industrializados — opcional para mercadinho
    # ---------------------------------------------------------------------------
    cst_ipi: Mapped[Optional[str]] = mapped_column(
        String(2),
        comment="CST IPI: 00,01,02,03,04,05,49,50,51,52,53,54,55,99",
    )
    aliq_ipi: Mapped[Optional[float]] = mapped_column(Numeric(7, 4))
    codigo_enquadramento_ipi: Mapped[Optional[str]] = mapped_column(
        String(3),
        comment="Código de Enquadramento do IPI — tabela TIPI",
    )

    # ---------------------------------------------------------------------------
    # Unidade tributável (quando difere da unidade comercial)
    # Ex: vende-se por unidade (UN) mas tributa-se por dúzia (DZ)
    # ---------------------------------------------------------------------------
    unidade_tributavel: Mapped[Optional[str]] = mapped_column(
        String(6),
        comment="Unidade tributável quando diferente da unidade comercial",
    )
    fator_conversao: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4),
        comment="Fator de conversão entre unidade comercial e tributável",
    )
    ean_tributavel: Mapped[Optional[str]] = mapped_column(
        String(14),
        comment="EAN da embalagem tributável quando diferente do produto",
    )

    # Relationships
    produtos: Mapped[list["Produto"]] = relationship(  # noqa: F821
        "Produto",
        back_populates="perfil_tributario",
        lazy="select",
    )
    itens_venda: Mapped[list["ItemVenda"]] = relationship(  # noqa: F821
        "ItemVenda",
        back_populates="perfil_tributario_historico",
        lazy="select",
    )
