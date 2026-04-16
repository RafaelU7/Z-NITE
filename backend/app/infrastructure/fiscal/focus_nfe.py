"""
FocusNFeGateway — implementação concreta do FiscalGateway para Focus NFe.

Documentação: https://focusnfe.com.br/documentacao/nfce/

Autenticação: HTTP Basic com (token, "").
Ambiente: controlado pela URL base — homologação ou produção.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.infrastructure.fiscal.gateway import (
    FiscalCancelResult,
    FiscalGateway,
    FiscalResult,
    FiscalStatusResult,
)

logger = logging.getLogger(__name__)

# Mapeamento status Focus NFe → status interno
_STATUS_MAP: dict[str, str] = {
    "autorizado": "emitida",
    "cancelado": "cancelada",
    "rejeitado": "rejeitada",
    "denegado": "rejeitada",
    "processando_autorizacao": "pendente",
    "erro_autorizacao": "rejeitada",
    "nao_cadastrado": "erro",
}

# Esses status indicam rejeição pela SEFAZ — não entra em retry
_REJECTION_STATUSES = frozenset({
    "rejeitado",
    "denegado",
    "erro_autorizacao",
})


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


class FocusNFeGateway(FiscalGateway):
    """
    Integração com a API v2 do Focus NFe.
    """

    def __init__(
        self,
        token: str,
        base_url: str = "https://homologacao.focusnfe.com.br",
        timeout: int = 30,
    ) -> None:
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def _make_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            auth=(self._token, ""),
            timeout=float(self._timeout),
            headers={"Content-Type": "application/json"},
        )

    async def emitir_nfce(
        self,
        ref: str,
        payload: dict[str, Any],
    ) -> FiscalResult:
        """
        POST /v2/nfce?ref={ref}

        Resposta 200/201 → processando ou já autorizado.
        Outros → erro técnico ou rejeição.
        """
        url = f"/v2/nfce"
        params = {"ref": ref}

        try:
            async with self._make_client() as client:
                response = await client.post(url, json=payload, params=params)
        except httpx.TimeoutException as exc:
            return FiscalResult(
                success=False,
                status="erro",
                error_message=f"Timeout ao emitir NFC-e: {exc}",
            )
        except httpx.RequestError as exc:
            return FiscalResult(
                success=False,
                status="erro",
                error_message=f"Erro de conexão com Focus NFe: {exc}",
            )

        logger.debug("Focus NFe emitir: status=%s body=%s", response.status_code, response.text[:500])

        try:
            data = response.json()
        except Exception:
            return FiscalResult(
                success=False,
                status="erro",
                error_message=f"Resposta não-JSON do provedor: HTTP {response.status_code}",
            )

        focus_status = data.get("status", "")
        is_rejection = focus_status in _REJECTION_STATUSES
        internal_status = _STATUS_MAP.get(focus_status, "erro")

        if response.status_code in (200, 201, 202):
            # Pode estar "processando_autorizacao" ou já "autorizado"
            return FiscalResult(
                success=internal_status == "emitida",
                status=internal_status,
                chave_acesso=data.get("chave_nfe") or data.get("chave_nfce"),
                numero=data.get("numero"),
                serie=data.get("serie"),
                data_autorizacao=_parse_datetime(data.get("data_autorizacao")),
                protocolo_autorizacao=data.get("protocolo"),
                xml_retorno=data.get("xml"),
                url_danfe=data.get("danfe_url") or data.get("caminho_danfe"),
                url_qrcode=data.get("qrcode_url") or data.get("caminho_qrcode"),
                url_consulta_nfe=data.get("caminho_consulta_nfe"),
                codigo_retorno=str(data.get("status_sefaz") or data.get("codigo_verificacao") or ""),
                mensagem_retorno=data.get("mensagem_sefaz") or data.get("mensagem") or "",
                is_rejection=is_rejection,
                provider_metadata=data,
            )

        if response.status_code == 422:
            # Rejeição de dados — payload inválido para o provedor
            erros = data.get("erros") or data.get("errors") or []
            mensagem = "; ".join(
                e.get("mensagem") or e.get("message") or str(e)
                for e in erros
            ) if isinstance(erros, list) else str(erros)
            return FiscalResult(
                success=False,
                status="rejeitada",
                is_rejection=True,
                mensagem_retorno=mensagem or "Dados inválidos para Focus NFe",
                provider_metadata=data,
            )

        # Outros erros HTTP (4xx, 5xx)
        mensagem = data.get("mensagem") or data.get("message") or str(data)
        return FiscalResult(
            success=False,
            status="erro",
            mensagem_retorno=mensagem,
            error_message=f"HTTP {response.status_code}: {mensagem}",
            is_rejection=is_rejection,
            provider_metadata=data,
        )

    async def consultar_status(self, ref: str) -> FiscalStatusResult:
        """GET /v2/nfce/{ref}?completo=1"""
        url = f"/v2/nfce/{ref}"
        params = {"completo": "1"}

        try:
            async with self._make_client() as client:
                response = await client.get(url, params=params)
        except httpx.RequestError as exc:
            return FiscalStatusResult(found=False)

        if response.status_code == 404:
            return FiscalStatusResult(found=False)

        try:
            data = response.json()
        except Exception:
            return FiscalStatusResult(found=False)

        focus_status = data.get("status", "")
        internal_status = _STATUS_MAP.get(focus_status, "erro")

        return FiscalStatusResult(
            found=True,
            status=internal_status,
            chave_acesso=data.get("chave_nfe") or data.get("chave_nfce"),
            protocolo_autorizacao=data.get("protocolo"),
            data_autorizacao=_parse_datetime(data.get("data_autorizacao")),
            numero=data.get("numero"),
            serie=data.get("serie"),
            codigo_retorno=str(data.get("status_sefaz") or ""),
            mensagem_retorno=data.get("mensagem_sefaz") or data.get("mensagem") or "",
            xml_retorno=data.get("xml"),
            url_danfe=data.get("danfe_url") or data.get("caminho_danfe"),
            url_qrcode=data.get("qrcode_url") or data.get("caminho_qrcode"),
            provider_metadata=data,
        )

    async def cancelar_nfce(self, ref: str, justificativa: str) -> FiscalCancelResult:
        """DELETE /v2/nfce/{ref} com justificativa no body."""
        url = f"/v2/nfce/{ref}"

        try:
            async with self._make_client() as client:
                response = await client.delete(
                    url,
                    json={"justificativa": justificativa},
                )
        except httpx.RequestError as exc:
            return FiscalCancelResult(
                success=False,
                mensagem=f"Erro de conexão ao cancelar: {exc}",
            )

        try:
            data = response.json()
        except Exception:
            return FiscalCancelResult(
                success=False,
                mensagem=f"Resposta não-JSON: HTTP {response.status_code}",
            )

        if response.status_code in (200, 204):
            return FiscalCancelResult(
                success=True,
                protocolo_cancelamento=data.get("protocolo"),
                xml_cancelamento=data.get("xml"),
                mensagem=data.get("mensagem") or "Cancelamento autorizado",
            )

        return FiscalCancelResult(
            success=False,
            mensagem=data.get("mensagem") or data.get("message") or f"HTTP {response.status_code}",
        )
