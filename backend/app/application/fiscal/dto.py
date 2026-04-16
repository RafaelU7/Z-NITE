"""DTOs do domínio Fiscal."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class DocumentoFiscalDTO(BaseModel):
    id: UUID
    empresa_id: UUID
    venda_id: Optional[UUID] = None
    operador_id: Optional[UUID] = None

    tipo: str
    status: str
    ambiente: str

    numero: Optional[int] = None
    serie: Optional[int] = None
    chave_acesso: Optional[str] = None

    tentativas: int = 0
    proxima_tentativa_em: Optional[datetime] = None

    data_emissao: Optional[datetime] = None
    data_autorizacao: Optional[datetime] = None
    protocolo_autorizacao: Optional[str] = None

    codigo_retorno: Optional[str] = None
    mensagem_retorno: Optional[str] = None

    url_danfe: Optional[str] = None
    url_qrcode: Optional[str] = None

    provider_id: Optional[str] = None
    provider_metadata: Optional[Any] = None

    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None

    model_config = {"from_attributes": True}
