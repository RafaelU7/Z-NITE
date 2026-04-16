"""
DTOs da camada de sincronização offline.

O endpoint POST /v1/sync/vendas recebe um lote de vendas que foram
finalizadas localmente enquanto o PDV estava sem internet.

Regra de idempotência: a chave_idempotencia é o identificador único
de deduplicação — se já existe uma venda com essa chave, ela é
classificada como "duplicada" (não cria novamente).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.infrastructure.database.models.enums import FormaPagamento, TipoEmissao


# ---------------------------------------------------------------------------
# Payload recebido do frontend
# ---------------------------------------------------------------------------


class ItemVendaSyncDTO(BaseModel):
    produto_id: UUID
    descricao_produto: str
    codigo_barras: Optional[str] = None
    unidade: Optional[str] = None
    sequencia: int = 1
    quantidade: Decimal = Field(gt=0)
    preco_unitario: Decimal = Field(gt=0)
    desconto_unitario: Decimal = Field(default=Decimal("0"), ge=0)
    snapshot_fiscal: Optional[Dict[str, Any]] = None


class PagamentoVendaSyncDTO(BaseModel):
    forma_pagamento: FormaPagamento
    valor: Decimal = Field(gt=0)
    troco: Decimal = Field(default=Decimal("0"), ge=0)
    nsu: Optional[str] = None
    bandeira_cartao: Optional[str] = None


class VendaSyncPayload(BaseModel):
    chave_idempotencia: UUID
    sessao_caixa_id: UUID
    origem_pdv: Optional[str] = None
    data_venda: Optional[datetime] = None
    tipo_emissao: TipoEmissao = TipoEmissao.FISCAL
    itens: List[ItemVendaSyncDTO] = Field(min_length=1)
    pagamentos: List[PagamentoVendaSyncDTO] = Field(min_length=1)


class SyncBatchRequest(BaseModel):
    vendas: List[VendaSyncPayload] = Field(min_length=1, max_length=100)


# ---------------------------------------------------------------------------
# Resposta ao frontend
# ---------------------------------------------------------------------------


class SyncResultAceita(BaseModel):
    chave_idempotencia: UUID
    venda_id: UUID
    documento_fiscal_id: Optional[UUID] = None  # None para vendas GERENCIAL


class SyncResultDuplicada(BaseModel):
    chave_idempotencia: UUID
    venda_id: UUID


class SyncResultRejeitada(BaseModel):
    chave_idempotencia: UUID
    motivo: str


class SyncBatchResponse(BaseModel):
    aceitas: List[SyncResultAceita] = []
    duplicadas: List[SyncResultDuplicada] = []
    rejeitadas: List[SyncResultRejeitada] = []
