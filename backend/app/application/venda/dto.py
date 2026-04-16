"""DTOs do domínio Venda / PDV."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.infrastructure.database.models.enums import FormaPagamento, TipoEmissao


class IniciarVendaRequest(BaseModel):
    sessao_caixa_id: UUID
    chave_idempotencia: Optional[UUID] = None
    data_venda: Optional[datetime] = None
    origem_pdv: Optional[str] = None


class FinalizarVendaRequest(BaseModel):
    tipo_emissao: TipoEmissao = TipoEmissao.FISCAL


class AdicionarItemRequest(BaseModel):
    produto_id: UUID
    quantidade: Decimal = Field(gt=0)
    preco_unitario: Optional[Decimal] = None  # None = usa preço do produto
    desconto_unitario: Decimal = Field(default=Decimal("0"), ge=0)


class AdicionarPagamentoRequest(BaseModel):
    forma_pagamento: FormaPagamento
    valor: Decimal = Field(gt=0)
    troco: Decimal = Field(default=Decimal("0"), ge=0)
    nsu: Optional[str] = None
    bandeira_cartao: Optional[str] = None
    autorizacao_cartao: Optional[str] = None


class ItemVendaDTO(BaseModel):
    id: UUID
    produto_id: UUID
    descricao_produto: str
    codigo_barras: Optional[str] = None
    unidade: Optional[str] = None
    sequencia: int
    quantidade: Decimal
    preco_unitario: Decimal
    desconto_unitario: Decimal
    total_item: Decimal
    cancelado: bool

    model_config = {"from_attributes": True}


class PagamentoDTO(BaseModel):
    id: UUID
    forma_pagamento: FormaPagamento
    valor: Decimal
    troco: Decimal
    nsu: Optional[str] = None
    bandeira_cartao: Optional[str] = None

    model_config = {"from_attributes": True}


class VendaDTO(BaseModel):
    id: UUID
    empresa_id: UUID
    sessao_caixa_id: UUID
    operador_id: UUID
    numero_venda_local: int
    status: str
    data_venda: datetime
    total_bruto: Decimal
    total_desconto: Decimal
    total_liquido: Decimal
    chave_idempotencia: Optional[UUID] = None
    tipo_emissao: TipoEmissao = TipoEmissao.FISCAL
    itens: List[ItemVendaDTO] = []
    pagamentos: List[PagamentoDTO] = []
    # Preenchido após finalizar — ID do DocumentoFiscal criado para esta venda (None para GERENCIAL)
    documento_fiscal_id: Optional[UUID] = None

    model_config = {"from_attributes": True}
