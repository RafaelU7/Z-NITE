"""
Modelo: SequenciaFiscal

Controle transacional de numeração fiscal (NFC-e / NF-e / SAT).

PROBLEMA RESOLVIDO:
  Manter contadores de numeração como colunas simples em `empresas` expõe
  o sistema a race conditions quando múltiplos caixas emitem documentos
  simultaneamente — dois terminais podem obter o mesmo número, resultando
  em rejeição pela SEFAZ (código 539 = duplicidade de nNF).

SOLUÇÃO:
  Tabela dedicada com linha por (empresa × tipo × série).
  O número é incrementado dentro de uma transação com SELECT FOR UPDATE,
  garantindo exclusividade absoluta mesmo com N caixas paralelos.

PADRÃO DE USO (repositório de NFC-e):

    from sqlalchemy import select
    from sqlalchemy.orm import Session

    def obter_proximo_numero(session: Session, empresa_id: UUID, tipo: str, serie: int) -> int:
        seq = session.execute(
            select(SequenciaFiscal)
            .where(SequenciaFiscal.empresa_id == empresa_id)
            .where(SequenciaFiscal.tipo == tipo)
            .where(SequenciaFiscal.serie == serie)
            .with_for_update()         # LOCK exclusivo na linha
        ).scalar_one()

        numero = seq.proximo_numero
        seq.proximo_numero += 1        # incremento atômico
        session.flush()                # persiste antes do commit
        return numero

MIGRAÇÃO:
  Os campos `serie_nfce` / `serie_nfe` permanecem em `Empresa` como
  referência de configuração, mas `proximo_numero_nfce` / `proximo_numero_nfe`
  foram removidos. Crie uma SequenciaFiscal por série ao provisionar a empresa.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class SequenciaFiscal(Base, TimestampMixin):
    """
    Contador de numeração fiscal por empresa / tipo / série.

    PK composta: (empresa_id, tipo, serie) — não usa UUID pois a combinação
    já é naturalmente única e o acesso é sempre por esses três campos.
    """
    __tablename__ = "sequencias_fiscais"
    __table_args__ = (
        # PK composta garante unicidade: uma linha por combinação empresa+tipo+série
        UniqueConstraint("empresa_id", "tipo", "serie", name="uq_sequencias_fiscais"),
        Index("ix_sequencias_fiscais_empresa_id", "empresa_id"),
        CheckConstraint("proximo_numero >= 1", name="ck_sequencia_numero_positivo"),
        CheckConstraint(
            "tipo IN ('nfce', 'nfe', 'sat')",
            name="ck_sequencia_tipo_valido",
        ),
        {
            "comment": (
                "Controle transacional de numeração fiscal. "
                "SEMPRE usar SELECT FOR UPDATE ao ler e incrementar."
            )
        },
    )

    # ---------------------------------------------------------------------------
    # Chave primária composta — acesso direto, sem UUID intermediário
    # ---------------------------------------------------------------------------
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    tipo: Mapped[str] = mapped_column(
        String(5),
        primary_key=True,
        comment="Tipo do documento: 'nfce' | 'nfe' | 'sat'",
    )
    serie: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        comment="Número da série fiscal (geralmente 1)",
    )

    # ---------------------------------------------------------------------------
    # Controle de numeração
    # ---------------------------------------------------------------------------
    proximo_numero: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Próximo número a ser emitido. Incrementar via SELECT FOR UPDATE.",
    )
    ultimo_numero_emitido: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Último número efetivamente autorizado pela SEFAZ (para diagnóstico)",
    )
    ultimo_numero_inutilizado: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Último número inutilizado (faixa com falha não recuperável)",
    )

    # Relationships
    empresa: Mapped["Empresa"] = relationship(  # noqa: F821
        "Empresa",
        back_populates="sequencias_fiscais",
        lazy="select",
    )
