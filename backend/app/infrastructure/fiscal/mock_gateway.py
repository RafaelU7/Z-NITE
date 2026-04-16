"""
MockFiscalGateway — implementação falsa para desenvolvimento local.

Usado automaticamente quando FOCUS_NFE_TOKEN está vazio.
Simula emissão bem-sucedida com dados fictícios para testes locais.
"""
from __future__ import annotations

import random
import string
from datetime import datetime, timezone
from typing import Any

from app.infrastructure.fiscal.gateway import (
    FiscalCancelResult,
    FiscalGateway,
    FiscalResult,
    FiscalStatusResult,
)


def _fake_chave_acesso() -> str:
    """Gera uma chave de acesso de 44 dígitos fictícia."""
    return "".join(random.choices(string.digits, k=44))


def _fake_protocolo() -> str:
    return "".join(random.choices(string.digits, k=15))


class MockFiscalGateway(FiscalGateway):
    """
    Gateway fiscal simulado para uso em ambiente de desenvolvimento.
    Retorna respostas bem-sucedidas sem acionar qualquer API externa.
    """

    async def emitir_nfce(
        self,
        ref: str,
        payload: dict[str, Any],
    ) -> FiscalResult:
        chave = _fake_chave_acesso()
        protocolo = _fake_protocolo()
        now = datetime.now(timezone.utc)

        return FiscalResult(
            success=True,
            status="emitida",
            chave_acesso=chave,
            numero=payload.get("numero"),
            serie=payload.get("serie"),
            data_autorizacao=now,
            protocolo_autorizacao=protocolo,
            xml_enviado=None,
            xml_retorno=f"<mock><chNFe>{chave}</chNFe><nProt>{protocolo}</nProt></mock>",
            url_danfe=f"https://mock.fiscal.local/danfe/{chave}.pdf",
            url_qrcode=f"https://mock.fiscal.local/qrcode/{chave}",
            codigo_retorno="100",
            mensagem_retorno="Autorizado o uso da NF-e (MOCK)",
            provider_id=f"mock-{ref}",
            provider_metadata={"ref": ref, "mock": True},
        )

    async def consultar_status(self, ref: str) -> FiscalStatusResult:
        return FiscalStatusResult(
            found=True,
            status="emitida",
            chave_acesso=_fake_chave_acesso(),
            protocolo_autorizacao=_fake_protocolo(),
            data_autorizacao=datetime.now(timezone.utc),
            codigo_retorno="100",
            mensagem_retorno="Autorizado o uso da NF-e (MOCK)",
            provider_metadata={"ref": ref, "mock": True},
        )

    async def cancelar_nfce(self, ref: str, justificativa: str) -> FiscalCancelResult:
        return FiscalCancelResult(
            success=True,
            protocolo_cancelamento=_fake_protocolo(),
            xml_cancelamento="<mock><xEvento>Cancelamento</xEvento></mock>",
            mensagem="Cancelamento autorizado (MOCK)",
        )
