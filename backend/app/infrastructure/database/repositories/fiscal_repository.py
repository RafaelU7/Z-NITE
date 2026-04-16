"""
FiscalRepository — criação de documentos fiscais pendentes.

Stub de integração fiscal:
  O sistema nunca gera XML, assina certificados ou chama a SEFAZ diretamente.
  Toda a comunicação é mediada por um provedor externo (Focus NFe, PlugNotas…)
  via FiscalGateway (a ser implementado na camada de infraestrutura).

  Ao finalizar uma venda, este repositório apenas insere um DocumentoFiscal
  com status=PENDENTE. Um worker assíncrono (Celery/ARQ) processará esse
  documento posteriormente e atualizará seu status.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.enums import (
    AmbienteFiscal,
    StatusDocumentoFiscal,
    TipoDocumentoFiscal,
)
from app.infrastructure.database.models.fiscal import DocumentoFiscal
from .base import BaseRepository


class FiscalRepository(BaseRepository[DocumentoFiscal]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DocumentoFiscal, session)

    async def criar_documento_pendente(
        self,
        empresa_id: UUID,
        venda_id: UUID,
        operador_id: UUID,
        ambiente: AmbienteFiscal = AmbienteFiscal.HOMOLOGACAO,
    ) -> DocumentoFiscal:
        """
        Cria um DocumentoFiscal com status PENDENTE para processamento assíncrono.
        Tipo padrão: NFC-e (modo PDV).
        """
        doc = DocumentoFiscal(
            empresa_id=empresa_id,
            venda_id=venda_id,
            operador_id=operador_id,
            tipo=TipoDocumentoFiscal.NFCE,
            status=StatusDocumentoFiscal.PENDENTE,
            ambiente=ambiente,
            tentativas=0,
        )
        return await self.save(doc)

    async def get_by_id_empresa(
        self,
        doc_id: UUID,
        empresa_id: UUID,
    ) -> Optional[DocumentoFiscal]:
        """Carrega um DocumentoFiscal verificando o dono (empresa_id)."""
        result = await self._session.execute(
            select(DocumentoFiscal)
            .where(DocumentoFiscal.id == doc_id)
            .where(DocumentoFiscal.empresa_id == empresa_id)
        )
        return result.scalar_one_or_none()

    async def get_by_venda_id(
        self,
        venda_id: UUID,
        empresa_id: UUID,
    ) -> Optional[DocumentoFiscal]:
        """Retorna o documento fiscal ativo para uma venda."""
        result = await self._session.execute(
            select(DocumentoFiscal)
            .where(DocumentoFiscal.venda_id == venda_id)
            .where(DocumentoFiscal.empresa_id == empresa_id)
            .order_by(DocumentoFiscal.criado_em.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_pendentes_para_processar(
        self,
        empresa_id: Optional[UUID] = None,
        limit: int = 50,
    ) -> list[DocumentoFiscal]:
        """Retorna documentos PENDENTE ou ERRO para reprocessamento em lote."""
        q = (
            select(DocumentoFiscal)
            .where(
                DocumentoFiscal.status.in_(
                    [StatusDocumentoFiscal.PENDENTE, StatusDocumentoFiscal.ERRO]
                )
            )
            .order_by(DocumentoFiscal.criado_em.asc())
            .limit(limit)
        )
        if empresa_id is not None:
            q = q.where(DocumentoFiscal.empresa_id == empresa_id)
        result = await self._session.execute(q)
        return list(result.scalars().all())
