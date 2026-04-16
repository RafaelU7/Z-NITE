"""
Modelo: DocumentoFiscal

Camada de abstração entre o sistema e o provedor fiscal externo.

REGRA DE OURO:
  Nenhum código desta aplicação gera XML NF-e/NFC-e manualmente,
  assina certificado digital ou faz chamadas SOAP para a SEFAZ.
  Todo o processo passa por um provedor externo (Focus NFe, PlugNotas, etc.)
  via FiscalGateway (camada de abstração da infraestrutura).

Design do fluxo fiscal:
  1. Venda é CONCLUÍDA (status = concluida) no PDV.
  2. Serviço fiscal cria um DocumentoFiscal com status PENDENTE.
  3. FiscalGateway envia os dados ao provedor externo.
  4. Provedor retorna status: EMITIDA (com chave e protocolo) ou REJEITADA.
  5. Sistema armazena o XML, chave de acesso, DANFE e protocolo.
  6. Em caso de rejeição: sistema registra o código/motivo e reprocessa.
  7. Em contingência: emite com flag de contingência, sincroniza depois.

Decisões importantes:
  - `xml_enviado` e `xml_retorno` são armazenados integralmente para auditoria.
    Em produção, avaliar compressão ou armazenamento em objeto (S3 / MinIO).
  - `tentativas` rastreia reprocessamento e ajuda a evitar loops infinitos.
  - A chave de acesso (44 dígitos) é única e identificável na SEFAZ para sempre.
  - Um documento por venda (NFC-e). NF-e de entrada é tratada separadamente.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .enums import AmbienteFiscal, StatusDocumentoFiscal, TipoDocumentoFiscal


class DocumentoFiscal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "documentos_fiscais"
    __table_args__ = (
        UniqueConstraint("chave_acesso", name="uq_doc_fiscal_chave_acesso"),
        Index("ix_doc_fiscal_empresa_id", "empresa_id"),
        Index("ix_doc_fiscal_venda_id", "venda_id"),
        Index("ix_doc_fiscal_status", "empresa_id", "status"),
        Index("ix_doc_fiscal_data_emissao", "empresa_id", "data_emissao"),
        # Índice para busca por chave de acesso (consulta na SEFAZ)
        Index("ix_doc_fiscal_chave_acesso", "chave_acesso"),
        # Índice para reprocessamento de documentos pendentes
        Index("ix_doc_fiscal_pendentes", "status", "tentativas"),
        # HARDENING: Apenas UM documento fiscal ativo por venda.
        # Partial unique: ignora documentos cancelados, rejeitados, inutilizados e com erro.
        # Garante que retries não criem um segundo documento ativo para a mesma venda.
        Index(
            "uq_doc_fiscal_venda_ativo",
            "venda_id",
            unique=True,
            postgresql_where=text(
                "venda_id IS NOT NULL AND "
                "status NOT IN ('cancelada', 'rejeitada', 'inutilizada', 'erro')"
            ),
        ),
        # HARDENING: FK composta garante que o documento pertence à venda da mesma empresa.
        ForeignKeyConstraint(
            ["empresa_id", "venda_id"],
            ["vendas.empresa_id", "vendas.id"],
            ondelete="SET NULL",
            name="fk_doc_fiscal_empresa_venda",
        ),
        {"comment": "Documentos fiscais emitidos via provedor externo (NFC-e, NF-e)"},
    )

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    venda_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendas.id", ondelete="SET NULL"),
        nullable=True,
        comment="NULL possível em caso de inutilização",
    )
    operador_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ---------------------------------------------------------------------------
    # Identificação do documento
    # ---------------------------------------------------------------------------
    tipo: Mapped[TipoDocumentoFiscal] = mapped_column(
        String(5),
        nullable=False,
        default=TipoDocumentoFiscal.NFCE,
    )
    numero: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Número sequencial da NF-e/NFC-e",
    )
    serie: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Série da NF-e/NFC-e",
    )
    chave_acesso: Mapped[Optional[str]] = mapped_column(
        String(44),
        comment="Chave de acesso de 44 dígitos — identificação única na SEFAZ",
    )

    # ---------------------------------------------------------------------------
    # Status e processamento
    # ---------------------------------------------------------------------------
    status: Mapped[StatusDocumentoFiscal] = mapped_column(
        String(20),
        nullable=False,
        default=StatusDocumentoFiscal.PENDENTE,
    )
    ambiente: Mapped[AmbienteFiscal] = mapped_column(
        String(1),
        nullable=False,
        default=AmbienteFiscal.HOMOLOGACAO,
    )

    # Controle de tentativas para evitar loop infinito de reprocessamento
    tentativas: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Número de tentativas de envio ao provedor",
    )
    proxima_tentativa_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Quando reagendar o próximo reprocessamento (backoff exponencial)",
    )

    # ---------------------------------------------------------------------------
    # Autorização SEFAZ
    # ---------------------------------------------------------------------------
    data_emissao: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Data/hora de emissão conforme informado ao provedor",
    )
    data_autorizacao: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Data/hora da autorização pela SEFAZ",
    )
    protocolo_autorizacao: Mapped[Optional[str]] = mapped_column(
        String(20),
        comment="nProt — número do protocolo de autorização da SEFAZ",
    )

    # ---------------------------------------------------------------------------
    # Retorno do provedor / SEFAZ
    # ---------------------------------------------------------------------------
    codigo_retorno: Mapped[Optional[str]] = mapped_column(
        String(6),
        comment="cStat — código de status da SEFAZ (100=autorizado, 302=dup, etc.)",
    )
    mensagem_retorno: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="xMotivo — descrição do retorno da SEFAZ",
    )

    # ---------------------------------------------------------------------------
    # Contingência
    # ---------------------------------------------------------------------------
    em_contingencia: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True = emitido em modo offline/contingência, aguardando SEFAZ",
    )
    tipo_contingencia: Mapped[Optional[str]] = mapped_column(
        String(5),
        comment="FS-DA (Formulário Segurança), EPEC, SVC-AN, SVC-RS",
    )
    data_entrada_contingencia: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    justificativa_contingencia: Mapped[Optional[str]] = mapped_column(
        String(256),
        comment="Texto obrigatório para justificar a contingência no XML",
    )

    # ---------------------------------------------------------------------------
    # Cancelamento
    # ---------------------------------------------------------------------------
    cancelada_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    protocolo_cancelamento: Mapped[Optional[str]] = mapped_column(String(20))
    motivo_cancelamento: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="xJust — justificativa de cancelamento (mínimo 15 chars, SEFAZ)",
    )

    # ---------------------------------------------------------------------------
    # XMLs e artefatos — armazenar integralmente para auditoria fiscal
    # ---------------------------------------------------------------------------
    xml_enviado: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="XML completo enviado ao provedor fiscal",
    )
    xml_retorno: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="XML de retorno/autorização da SEFAZ (com protocolo)",
    )
    xml_cancelamento: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="XML de evento de cancelamento autorizado",
    )

    # URLs geradas pelo provedor
    url_danfe: Mapped[Optional[str]] = mapped_column(
        String(500),
        comment="URL do DANFE/DANFCe PDF gerado pelo provedor",
    )
    url_qrcode: Mapped[Optional[str]] = mapped_column(
        String(1000),
        comment="URL do QR Code para NFC-e",
    )
    url_consulta_nfe: Mapped[Optional[str]] = mapped_column(
        String(200),
        comment="URL de consulta do NFC-e site governamental",
    )

    # Metadata do provedor externo para rastreio
    provider_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="ID do documento no sistema do provedor (Focus NFe, PlugNotas, etc.)",
    )
    provider_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        comment="Dados extras retornados pelo provedor (para troubleshooting)",
    )

    # Relationships
    venda: Mapped[Optional["Venda"]] = relationship(  # noqa: F821
        "Venda",
        back_populates="documento_fiscal",
        foreign_keys=[venda_id],
        lazy="select",
    )
