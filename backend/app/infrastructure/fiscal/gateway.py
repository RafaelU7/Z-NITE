"""
FiscalGateway — abstração do provedor de emissão fiscal externo.

Regra de ouro do projeto:
  Nenhum código desta aplicação assina certificados NF-e, gera XML manualmente
  ou faz chamadas diretas ao SOAP da SEFAZ. Todo o processamento passa por
  um provedor externo (Focus NFe, PlugNotas, etc.) via esta interface.

Implementações concretas: FocusNFeGateway, MockFiscalGateway.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class FiscalResult:
    """Resultado da tentativa de emissão de um documento fiscal."""
    success: bool
    # "emitida" | "rejeitada" | "erro" | "pendente"
    status: str
    codigo_retorno: Optional[str] = None
    mensagem_retorno: Optional[str] = None
    chave_acesso: Optional[str] = None
    numero: Optional[int] = None
    serie: Optional[int] = None
    data_autorizacao: Optional[datetime] = None
    protocolo_autorizacao: Optional[str] = None
    xml_enviado: Optional[str] = None
    xml_retorno: Optional[str] = None
    url_danfe: Optional[str] = None
    url_qrcode: Optional[str] = None
    url_consulta_nfe: Optional[str] = None
    provider_id: Optional[str] = None
    provider_metadata: dict[str, Any] = field(default_factory=dict)
    # True se a SEFAZ rejeitou o documento — não deve entrar em retry automático
    is_rejection: bool = False
    # Mensagem técnica de erro (conexão, timeout, parse, etc.)
    error_message: Optional[str] = None


@dataclass
class FiscalStatusResult:
    """Resultado da consulta de status de um documento fiscal no provedor."""
    found: bool
    status: Optional[str] = None
    chave_acesso: Optional[str] = None
    protocolo_autorizacao: Optional[str] = None
    data_autorizacao: Optional[datetime] = None
    numero: Optional[int] = None
    serie: Optional[int] = None
    codigo_retorno: Optional[str] = None
    mensagem_retorno: Optional[str] = None
    xml_retorno: Optional[str] = None
    url_danfe: Optional[str] = None
    url_qrcode: Optional[str] = None
    provider_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FiscalCancelResult:
    """Resultado da solicitação de cancelamento de NFC-e."""
    success: bool
    protocolo_cancelamento: Optional[str] = None
    xml_cancelamento: Optional[str] = None
    mensagem: Optional[str] = None


class FiscalGateway(ABC):
    """
    Interface abstrata para provedores de emissão fiscal.
    Implementações concretas: FocusNFeGateway, MockFiscalGateway.
    """

    @abstractmethod
    async def emitir_nfce(
        self,
        ref: str,
        payload: dict[str, Any],
    ) -> FiscalResult:
        """Envia a NFC-e para o provedor e aguarda a resposta."""
        ...

    @abstractmethod
    async def consultar_status(
        self,
        ref: str,
    ) -> FiscalStatusResult:
        """Consulta o status atual de um documento no provedor."""
        ...

    @abstractmethod
    async def cancelar_nfce(
        self,
        ref: str,
        justificativa: str,
    ) -> FiscalCancelResult:
        """Solicita cancelamento de NFC-e autorizada."""
        ...
