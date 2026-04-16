"""
Modelo: Usuário e Permissões

Segurança operacional por perfil de acesso.
Histórico de último acesso para auditoria.

Decisão arquitetural:
  - O campo senha_hash armazena bcrypt. O custo mínimo recomendado é 12.
  - Perfis predefinidos cobrem 95% dos casos do varejo. Permissões extras
    (granulares) podem ser adicionadas em PermissaoExtra quando necessário.
  - O campo empresa_id permite isolamento multi-tenant no futuro.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .enums import PerfilUsuario


class Usuario(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "usuarios"
    __table_args__ = (
        UniqueConstraint("empresa_id", "email", name="uq_usuarios_empresa_email"),
        # HARDENING: unicidade do código de operador por empresa.
        # Impede ambiguidade no login rápido por código numérico no PDV.
        UniqueConstraint("empresa_id", "codigo_operador", name="uq_usuarios_empresa_codigo_operador"),
        Index("ix_usuarios_empresa_id", "empresa_id"),
        Index("ix_usuarios_email", "email"),
        {"comment": "Operadores, gerentes e administradores do sistema"},
    )

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
    )

    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    senha_hash: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Hash bcrypt — custo mínimo 12",
    )

    perfil: Mapped[PerfilUsuario] = mapped_column(
        String(20),
        nullable=False,
        default=PerfilUsuario.OPERADOR_CAIXA,
        comment="Perfil de acesso que define permissões base",
    )

    # Identificação operacional
    codigo_operador: Mapped[Optional[str]] = mapped_column(
        String(20),
        comment="Código curto para login rápido no PDV (numérico, ex: 001)",
    )
    pin_hash: Mapped[Optional[str]] = mapped_column(
        String(200),
        comment="PIN de 4-6 dígitos para login rápido no caixa (bcrypt)",
    )

    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ultimo_acesso: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    empresa: Mapped["Empresa"] = relationship(  # noqa: F821
        "Empresa",
        back_populates="usuarios",
        lazy="select",
    )
    sessoes_caixa: Mapped[list["SessaoCaixa"]] = relationship(  # noqa: F821
        "SessaoCaixa",
        back_populates="operador",
        foreign_keys="SessaoCaixa.operador_id",
        lazy="select",
    )
    vendas: Mapped[list["Venda"]] = relationship(  # noqa: F821
        "Venda",
        back_populates="operador",
        foreign_keys="Venda.operador_id",
        lazy="select",
    )
    movimentacoes_estoque: Mapped[list["MovimentacaoEstoque"]] = relationship(  # noqa: F821
        "MovimentacaoEstoque",
        back_populates="usuario",
        lazy="select",
    )
    logs_auditoria: Mapped[list["LogAuditoria"]] = relationship(  # noqa: F821
        "LogAuditoria",
        back_populates="usuario",
        lazy="select",
    )
