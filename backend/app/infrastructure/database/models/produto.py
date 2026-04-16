"""
Modelos: Categoria, UnidadeMedida, Produto, ProdutoEAN

O catálogo de produtos é o núcleo do sistema. Decisões críticas:

  - Categoria suporta hierarquia (pai/filho) via auto-referência, mas
    o sistema deve limitar a 2-3 níveis para evitar complexidade na UI.

  - Produto mantém custo médio ponderado (atualizado via MovimentacaoEstoque).

  - Múltiplos EANs por produto (ProdutoEAN) resolvem o problema real do varejo:
    produto com embalagem diferente (unidade / caixa / fardo) com EANs distintos.

  - Produto pesável usa qty_decimal=3. Produto unitário usa qty_decimal=0.

  - Margem é calculada pela camada de serviço, não armazenada diretamente,
    pois depende do custo médio atualizado. Porém um snapshot de margem
    pode ser útil para o dashboard — use campo `margem_calculada` para isso.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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
from .enums import TipoUnidade


class Categoria(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "categorias"
    __table_args__ = (
        UniqueConstraint("empresa_id", "nome", "categoria_pai_id", name="uq_categorias_nome"),
        Index("ix_categorias_empresa_id", "empresa_id"),
        {"comment": "Categorias hierárquicas de produtos (máx. 3 níveis recomendados)"},
    )

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
    )

    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(Text)

    # Auto-referência para hierarquia
    categoria_pai_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categorias.id", ondelete="SET NULL"),
        nullable=True,
        comment="NULL = categoria raiz",
    )

    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    categoria_pai: Mapped[Optional["Categoria"]] = relationship(
        "Categoria",
        remote_side="Categoria.id",
        back_populates="subcategorias",
        lazy="select",
    )
    subcategorias: Mapped[list["Categoria"]] = relationship(
        "Categoria",
        back_populates="categoria_pai",
        lazy="select",
    )
    produtos: Mapped[list["Produto"]] = relationship(
        "Produto",
        back_populates="categoria",
        lazy="select",
    )


class UnidadeMedida(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "unidades_medida"
    __table_args__ = (
        UniqueConstraint("empresa_id", "codigo", name="uq_unidades_medida_codigo"),
        Index("ix_unidades_medida_empresa_id", "empresa_id"),
        {"comment": "Unidades de medida comercial: UN, KG, LT, CX, DZ, etc."},
    )

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
    )

    codigo: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
        comment="Código padrão: UN, KG, G, LT, ML, CX, DZ, PCT",
    )
    descricao: Mapped[str] = mapped_column(String(50), nullable=False)
    tipo: Mapped[TipoUnidade] = mapped_column(
        String(10),
        nullable=False,
        default=TipoUnidade.UNITARIA,
    )
    casas_decimais: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="0 para unitário, 3 para pesável (kg com 3 casas)",
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    produtos: Mapped[list["Produto"]] = relationship(
        "Produto",
        back_populates="unidade",
        lazy="select",
    )


class Produto(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "produtos"
    __table_args__ = (
        UniqueConstraint("empresa_id", "sku", name="uq_produtos_sku"),
        UniqueConstraint("empresa_id", "codigo_barras_principal", name="uq_produtos_ean"),
        Index("ix_produtos_empresa_id", "empresa_id"),
        Index("ix_produtos_categoria_id", "categoria_id"),
        # Índice crítico: busca por EAN no momento da venda deve ser < 10ms
        Index("ix_produtos_ean_principal", "codigo_barras_principal"),
        Index("ix_produtos_ativo", "empresa_id", "ativo"),
        CheckConstraint("preco_venda >= 0", name="ck_produtos_preco_positivo"),
        CheckConstraint("custo_medio >= 0", name="ck_produtos_custo_positivo"),
        CheckConstraint("estoque_minimo >= 0", name="ck_produtos_estoque_minimo_positivo"),
        # HARDENING: Produto ativo sem perfil tributário não pode ser vendido
        # (não há dados para emissão da NFC-e). O perfil é opcional apenas durante
        # o cadastro inicial (ativo=false) até ser configurado completamente.
        CheckConstraint(
            "ativo = false OR perfil_tributario_id IS NOT NULL",
            name="ck_produto_ativo_requer_fiscal",
        ),
        {"comment": "Catálogo de produtos com dados comerciais e fiscais"},
    )

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # ---------------------------------------------------------------------------
    # Identificação
    # ---------------------------------------------------------------------------
    sku: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Stock Keeping Unit — código interno do produto",
    )
    codigo_barras_principal: Mapped[Optional[str]] = mapped_column(
        String(14),
        comment="EAN-13 ou DUN-14 principal. Demais EANs em produto_eans.",
    )
    descricao: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Descrição completa para NF-e / cadastro",
    )
    descricao_pdv: Mapped[Optional[str]] = mapped_column(
        String(60),
        comment="Descrição curta exibida no PDV e no recibo (≤60 chars)",
    )
    marca: Mapped[Optional[str]] = mapped_column(String(100))
    observacao: Mapped[Optional[str]] = mapped_column(Text)

    # ---------------------------------------------------------------------------
    # Classificação
    # ---------------------------------------------------------------------------
    categoria_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categorias.id", ondelete="SET NULL"),
        nullable=True,
    )
    unidade_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("unidades_medida.id", ondelete="RESTRICT"),
        nullable=False,
    )

    pesavel: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True = produto vendido por peso (balança). Preço por kg.",
    )
    balanca_codigo: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Código PLU para balança integrada (1-5 dígitos)",
    )

    # ---------------------------------------------------------------------------
    # Precificação e custo
    # Precisão Numeric(15,4): armazena até R$ 99.999.999.999,9999
    # ---------------------------------------------------------------------------
    preco_venda: Mapped[float] = mapped_column(
        Numeric(15, 4),
        nullable=False,
        default=0,
        comment="Preço de venda atual em R$",
    )
    custo_medio: Mapped[float] = mapped_column(
        Numeric(15, 4),
        nullable=False,
        default=0,
        comment="Custo médio ponderado, atualizado a cada entrada de estoque",
    )
    margem_calculada: Mapped[Optional[float]] = mapped_column(
        Numeric(7, 4),
        comment="Margem bruta em % — snapshot calculado. Não usar como fonte primária.",
    )

    # ---------------------------------------------------------------------------
    # Estoque
    # ---------------------------------------------------------------------------
    estoque_minimo: Mapped[float] = mapped_column(
        Numeric(15, 3),
        nullable=False,
        default=0,
        comment="Quantidade mínima de estoque para alerta de ruptura",
    )
    controla_estoque: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="False = produto de serviço ou que não controla estoque",
    )

    # ---------------------------------------------------------------------------
    # Fiscal — FK para o perfil tributário ativo
    # ---------------------------------------------------------------------------
    perfil_tributario_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("perfis_tributarios.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Perfil tributário ativo. Sempre referenciar a versão vigente.",
    )

    # ---------------------------------------------------------------------------
    # Status
    # ---------------------------------------------------------------------------
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    destaque_pdv: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Exibir como produto em destaque na tela do PDV",
    )

    # Relationships
    categoria: Mapped[Optional["Categoria"]] = relationship(
        "Categoria",
        back_populates="produtos",
        lazy="select",
    )
    unidade: Mapped["UnidadeMedida"] = relationship(
        "UnidadeMedida",
        back_populates="produtos",
        lazy="select",
    )
    perfil_tributario: Mapped[Optional["PerfilTributario"]] = relationship(  # noqa: F821
        "PerfilTributario",
        back_populates="produtos",
        lazy="select",
    )
    eans: Mapped[list["ProdutoEAN"]] = relationship(
        "ProdutoEAN",
        back_populates="produto",
        lazy="select",
        cascade="all, delete-orphan",
    )
    estoques: Mapped[list["Estoque"]] = relationship(  # noqa: F821
        "Estoque",
        back_populates="produto",
        lazy="select",
    )
    estoque: Mapped[Optional["Estoque"]] = relationship(  # noqa: F821
        "Estoque",
        primaryjoin="and_(foreign(Estoque.produto_id) == Produto.id, Estoque.principal == True)",
        back_populates="produto",
        uselist=False,
        lazy="select",
        viewonly=True,
        doc="Saldo no local principal. Para todos os locais, use .estoques",
    )
    movimentacoes_estoque: Mapped[list["MovimentacaoEstoque"]] = relationship(  # noqa: F821
        "MovimentacaoEstoque",
        back_populates="produto",
        lazy="select",
    )
    itens_venda: Mapped[list["ItemVenda"]] = relationship(  # noqa: F821
        "ItemVenda",
        back_populates="produto",
        lazy="select",
    )


class ProdutoEAN(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    EANs adicionais de um produto.

    Casos de uso:
      - Produto vendido na unidade E em caixa com EANs distintos
      - Embalagens de fornecedores diferentes com EANs diferentes
      - Reembalagens internas
    """
    __tablename__ = "produto_eans"
    __table_args__ = (
        UniqueConstraint("empresa_id", "ean", name="uq_produto_eans_ean"),
        Index("ix_produto_eans_produto_id", "produto_id"),
        # Índice crítico: o PDV busca produtos por qualquer EAN associado
        Index("ix_produto_eans_ean", "ean"),
        {"comment": "EANs alternativos associados ao produto (leitura de barcode)"},
    )

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    produto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("produtos.id", ondelete="CASCADE"),
        nullable=False,
    )
    ean: Mapped[str] = mapped_column(String(14), nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="Ex: 'Caixa com 12 unidades', 'Embalagem promocional'",
    )
    fator_quantidade: Mapped[float] = mapped_column(
        Numeric(10, 4),
        nullable=False,
        default=1,
        comment="Quantas unidades do produto este EAN representa. Ex: 12 para caixa.",
    )
    principal: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="EAN principal exibido no cadastro (redundância com produto.codigo_barras_principal)",
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    produto: Mapped["Produto"] = relationship(
        "Produto",
        back_populates="eans",
        lazy="select",
    )
