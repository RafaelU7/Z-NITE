"""
Modelo: LogAuditoria

Trilha de auditoria de todas as ações sensíveis do sistema.

O que deve ser auditado:
  - Alteração de preço de produto
  - Alteração de perfil tributário
  - Cancelamento de venda
  - Cancelamento de item
  - Sangria / suprimento
  - Abertura / fechamento de caixa
  - Desconto acima do limite
  - Alteração de senha
  - Criação / inativação de usuário
  - Alteração de configuração fiscal da empresa
  - Qualquer operação que exija permissão especial

Design:
  - Imutável: nunca altere ou delete um log de auditoria.
  - `dados_anteriores` e `dados_novos` em JSONB para rastrear exatamente o que mudou.
  - `ip_address` para identificação de origem (em uso SaaS futuro).
  - Tabela separada da aplicação garante que erros no sistema não apaguem trilha.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LogAuditoria(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "log_auditoria"
    __table_args__ = (
        Index("ix_log_auditoria_empresa_id", "empresa_id"),
        Index("ix_log_auditoria_usuario_id", "usuario_id"),
        Index("ix_log_auditoria_tabela_registro", "tabela_afetada", "registro_id"),
        Index("ix_log_auditoria_criado_em", "criado_em"),
        # Índice para busca por ação específica (ex: todos os cancelamentos)
        Index("ix_log_auditoria_acao", "empresa_id", "acao"),
        {"comment": "Trilha de auditoria imutável de todas as operações sensíveis"},
    )

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    usuario_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        comment="NULL = ação do sistema (automação, scheduler, etc.)",
    )

    acao: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment=(
            "Código da ação auditada. Ex: 'venda.cancelar', 'produto.alterar_preco', "
            "'caixa.sangria', 'usuario.alterar_senha'"
        ),
    )
    tabela_afetada: Mapped[Optional[str]] = mapped_column(
        String(60),
        comment="Nome da tabela do banco afetada pela operação",
    )
    registro_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        comment="UUID do registro afetado na tabela",
    )

    dados_anteriores: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        comment="Estado do registro ANTES da operação (snapshot)",
    )
    dados_novos: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        comment="Estado do registro APÓS a operação (snapshot)",
    )

    descricao: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Descrição legível da ação para exibição no relatório de auditoria",
    )

    # Rastreabilidade de origem
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        comment="IP do cliente (IPv4 ou IPv6)",
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(300),
        comment="User-Agent do browser/app (para diagnóstico)",
    )
    # HARDENING: FK explícita para sessão de caixa — garante rastreabilidade
    # referencial. ondelete=SET NULL preserva o log mesmo após sessão deletada.
    sessao_caixa_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessoes_caixa.id", ondelete="SET NULL"),
        nullable=True,
        comment="Sessão do caixa ativa quando a ação foi realizada",
    )

    # Relationships
    usuario: Mapped[Optional["Usuario"]] = relationship(  # noqa: F821
        "Usuario",
        back_populates="logs_auditoria",
        lazy="select",
    )
