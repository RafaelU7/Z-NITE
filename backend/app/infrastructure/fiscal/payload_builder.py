"""
FiscalPayloadBuilder — monta o payload JSON para envio ao provedor Focus NFe.

Recebe entidades do domínio (Venda + Empresa + numeração) e produz o dict
no formato exigido pela API Focus NFe v2 para NFC-e (modelo 65).

Referência: https://focusnfe.com.br/documentacao/nfce/
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.infrastructure.database.models.empresa import Empresa
from app.infrastructure.database.models.enums import FormaPagamento
from app.infrastructure.database.models.venda import Venda

# Mapeamento do enum interno → código TabPag NF-e
_FORMA_PAG_MAP: dict[str, str] = {
    FormaPagamento.DINHEIRO: "01",
    FormaPagamento.CHEQUE: "02",
    FormaPagamento.CARTAO_CREDITO: "03",
    FormaPagamento.CARTAO_DEBITO: "04",
    FormaPagamento.CREDITO_LOJA: "05",
    FormaPagamento.VALE_ALIMENTACAO: "10",
    FormaPagamento.VALE_REFEICAO: "11",
    FormaPagamento.VALE_PRESENTE: "12",
    FormaPagamento.VALE_COMBUSTIVEL: "13",
    FormaPagamento.PIX: "17",
    FormaPagamento.OUTROS: "99",
}


_AMBIENTE_MAP: dict[str, str] = {
    "1": "producao",
    "2": "homologacao",
}


def build_nfce_payload(
    venda: Venda,
    empresa: Empresa,
    numero: int,
    serie: int,
) -> dict[str, Any]:
    """
    Monta o payload no formato Focus NFe v2 para NFC-e (modelo 65).
    Retorna um dict serializável em JSON.
    """
    data_emissao_iso = (
        venda.data_venda if venda.data_venda else datetime.now(timezone.utc)
    ).isoformat()

    itens_ativos = [i for i in (venda.itens or []) if not i.cancelado]
    pagamentos = venda.pagamentos or []

    items: list[dict[str, Any]] = []
    for idx, item in enumerate(itens_ativos, start=1):
        qtd = float(item.quantidade)
        preco_unit = float(item.preco_unitario)
        desconto_unit = float(item.desconto_unitario) if item.desconto_unitario else 0.0
        preco_liquido = preco_unit - desconto_unit
        valor_bruto_item = preco_unit * qtd
        valor_total = float(item.total_item)

        item_payload: dict[str, Any] = {
            "numero_item": str(idx),
            "codigo_produto": item.codigo_barras or f"ITEM{idx:04d}",
            "descricao": item.descricao_produto,
            "codigo_ncm": item.ncm or "00000000",
            "cfop": item.cfop or "5102",
            "unidade_comercial": item.unidade or "UN",
            "quantidade_comercial": f"{qtd:.4f}",
            "valor_unitario_comercial": f"{preco_liquido:.10f}",
            "valor_total_bruto": f"{valor_bruto_item:.2f}",
            "valor_item": f"{valor_total:.2f}",
            "icms_origem_mercadoria": (
                item.origem if isinstance(item.origem, str) else "0"
            ),
        }

        if desconto_unit > 0:
            item_payload["valor_desconto"] = f"{desconto_unit * qtd:.2f}"

        # Tributação ICMS — CSOSN (Simples Nacional) ou CST (outros regimes)
        if item.csosn:
            item_payload["icms_situacao_tributaria"] = item.csosn
        elif item.cst_icms:
            item_payload["icms_situacao_tributaria"] = item.cst_icms
        else:
            item_payload["icms_situacao_tributaria"] = "400"  # default SN sem ICMS

        # Alíquota ICMS (somente se aplicável)
        if item.aliq_icms and float(item.aliq_icms) > 0:
            item_payload["icms_aliquota"] = f"{float(item.aliq_icms):.2f}"

        # PIS
        item_payload["pis_situacao_tributaria"] = item.cst_pis or "07"
        if item.aliq_pis and float(item.aliq_pis) > 0:
            item_payload["pis_aliquota_percentual"] = f"{float(item.aliq_pis):.4f}"

        # COFINS
        item_payload["cofins_situacao_tributaria"] = item.cst_cofins or "07"
        if item.aliq_cofins and float(item.aliq_cofins) > 0:
            item_payload["cofins_aliquota_percentual"] = f"{float(item.aliq_cofins):.4f}"

        # CEST — Código Especificador de Substituição Tributária
        if item.cest:
            item_payload["codigo_cest"] = item.cest

        items.append(item_payload)

    # Formas de pagamento
    formas: list[dict[str, Any]] = []
    troco_total = 0.0
    for pag in pagamentos:
        forma_value = (
            pag.forma_pagamento
            if isinstance(pag.forma_pagamento, str)
            else pag.forma_pagamento.value
        )
        codigo_forma = _FORMA_PAG_MAP.get(forma_value, "99")
        formas.append({
            "forma_pagamento": codigo_forma,
            "valor_pagamento": f"{float(pag.valor):.2f}",
        })
        if pag.troco:
            troco_total += float(pag.troco)

    if troco_total > 0:
        formas[-1]["troco"] = f"{troco_total:.2f}"

    payload: dict[str, Any] = {
        "natureza_operacao": "VENDA AO CONSUMIDOR",
        "data_emissao": data_emissao_iso,
        "tipo_documento": 1,        # 1=Saída
        "presenca_comprador": 1,    # 1=Operação presencial
        "consumidor_final": 1,
        "finalidade_emissao": 1,    # 1=NF-e normal
        "cnpj_emitente": empresa.cnpj,
        "items": items,
        "formas_pagamento": formas,
    }

    # Ambiente fiscal
    if empresa.ambiente_fiscal:
        ambiente_val = empresa.ambiente_fiscal if isinstance(empresa.ambiente_fiscal, str) else empresa.ambiente_fiscal.value
        payload["ambiente"] = _AMBIENTE_MAP.get(ambiente_val, "homologacao")

    return payload


def payload_to_audit_string(payload: dict[str, Any]) -> str:
    """Serializa o payload para armazenamento seguro no campo xml_enviado."""
    return json.dumps(payload, ensure_ascii=False, default=str)
