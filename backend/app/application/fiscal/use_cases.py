"""Use cases do domínio Fiscal."""
from __future__ import annotations

from uuid import UUID

from app.application.fiscal.dto import DocumentoFiscalDTO
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.infrastructure.database.models.enums import StatusDocumentoFiscal
from app.infrastructure.database.repositories.fiscal_repository import FiscalRepository


def _to_dto(doc) -> DocumentoFiscalDTO:
    return DocumentoFiscalDTO(
        id=doc.id,
        empresa_id=doc.empresa_id,
        venda_id=doc.venda_id,
        operador_id=doc.operador_id,
        tipo=doc.tipo if isinstance(doc.tipo, str) else doc.tipo.value,
        status=doc.status if isinstance(doc.status, str) else doc.status.value,
        ambiente=doc.ambiente if isinstance(doc.ambiente, str) else doc.ambiente.value,
        numero=doc.numero,
        serie=doc.serie,
        chave_acesso=doc.chave_acesso,
        tentativas=doc.tentativas,
        proxima_tentativa_em=doc.proxima_tentativa_em,
        data_emissao=doc.data_emissao,
        data_autorizacao=doc.data_autorizacao,
        protocolo_autorizacao=doc.protocolo_autorizacao,
        codigo_retorno=doc.codigo_retorno,
        mensagem_retorno=doc.mensagem_retorno,
        url_danfe=doc.url_danfe,
        url_qrcode=doc.url_qrcode,
        provider_id=doc.provider_id,
        provider_metadata=doc.provider_metadata,
        criado_em=doc.criado_em,
        atualizado_em=doc.atualizado_em,
    )


class ConsultarStatusDocumentoUseCase:
    """Retorna o documento fiscal de uma empresa por ID."""

    def __init__(self, repo: FiscalRepository) -> None:
        self._repo = repo

    async def execute(self, doc_id: UUID, empresa_id: UUID) -> DocumentoFiscalDTO:
        doc = await self._repo.get_by_id_empresa(doc_id, empresa_id)
        if not doc:
            raise NotFoundError("Documento fiscal não encontrado.")
        return _to_dto(doc)


class GetDocumentoPorVendaUseCase:
    """Retorna o documento fiscal ativo de uma venda."""

    def __init__(self, repo: FiscalRepository) -> None:
        self._repo = repo

    async def execute(self, venda_id: UUID, empresa_id: UUID) -> DocumentoFiscalDTO:
        doc = await self._repo.get_by_venda_id(venda_id, empresa_id)
        if not doc:
            raise NotFoundError("Documento fiscal não encontrado para esta venda.")
        return _to_dto(doc)


class ReprocessarDocumentoUseCase:
    """
    Redefine o status do documento para PENDENTE, para que o worker o reprocesse.
    Só é permitido para documentos REJEITADOS ou com ERRO.
    A responsabilidade de enfileirar o job ARQ fica na camada de router.
    """

    def __init__(self, repo: FiscalRepository) -> None:
        self._repo = repo

    async def execute(self, doc_id: UUID, empresa_id: UUID) -> DocumentoFiscalDTO:
        doc = await self._repo.get_by_id_empresa(doc_id, empresa_id)
        if not doc:
            raise NotFoundError("Documento fiscal não encontrado.")

        if doc.status not in (
            StatusDocumentoFiscal.REJEITADA,
            StatusDocumentoFiscal.ERRO,
        ):
            raise BusinessRuleError(
                f"Apenas documentos com status REJEITADA ou ERRO podem ser "
                f"reprocessados. Status atual: {doc.status}"
            )

        doc.status = StatusDocumentoFiscal.PENDENTE
        doc.tentativas = 0
        doc.proxima_tentativa_em = None
        doc.codigo_retorno = None
        doc.mensagem_retorno = None
        await self._repo._session.flush()

        return _to_dto(doc)
