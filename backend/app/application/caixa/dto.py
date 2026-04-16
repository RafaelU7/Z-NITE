"""DTOs do domínio Caixa / Sessão de Caixa."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AbrirSessaoRequest(BaseModel):
    caixa_id: UUID
    saldo_abertura: Decimal = Field(default=Decimal("0"), ge=0)


class FecharSessaoRequest(BaseModel):
    saldo_informado_fechamento: Decimal = Field(ge=0)
    observacao: Optional[str] = None


class SessaoCaixaDTO(BaseModel):
    id: UUID
    empresa_id: UUID
    caixa_id: UUID
    operador_id: UUID
    status: str
    data_abertura: datetime
    saldo_abertura: Decimal
    data_fechamento: Optional[datetime] = None
    operador_fechamento_id: Optional[UUID] = None
    saldo_informado_fechamento: Optional[Decimal] = None
    saldo_sistema_fechamento: Optional[Decimal] = None
    diferenca_fechamento: Optional[Decimal] = None
    total_vendas_bruto: Decimal = Decimal("0")
    total_descontos: Decimal = Decimal("0")
    total_liquido: Decimal = Decimal("0")
    total_dinheiro: Decimal = Decimal("0")
    total_pix: Decimal = Decimal("0")
    total_cartao_debito: Decimal = Decimal("0")
    total_cartao_credito: Decimal = Decimal("0")
    total_outros: Decimal = Decimal("0")
    quantidade_vendas: int = 0
    ticket_medio: Optional[Decimal] = None
    observacao_fechamento: Optional[str] = None

    model_config = {"from_attributes": True}
