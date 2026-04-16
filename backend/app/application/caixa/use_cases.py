"""
Use cases do domínio Caixa.

AbrirSessaoUseCase    — POST /v1/caixa/sessoes
GetSessaoAtivaUseCase — GET  /v1/caixa/sessao-ativa?caixa_id=
FecharSessaoUseCase   — POST /v1/caixa/sessoes/{sessao_id}/fechar
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.infrastructure.database.models.caixa import SessaoCaixa
from app.infrastructure.database.models.enums import StatusSessaoCaixa
from app.infrastructure.database.repositories.caixa_repository import CaixaRepository

from .dto import AbrirSessaoRequest, FecharSessaoRequest, SessaoCaixaDTO


def _to_dto(sessao: SessaoCaixa) -> SessaoCaixaDTO:
    def _dec(value) -> Decimal:
        return (
            Decimal(str(value)).quantize(Decimal("0.0001"))
            if value is not None
            else Decimal("0.0000")
        )

    def _dec_opt(value) -> Decimal | None:
        return (
            Decimal(str(value)).quantize(Decimal("0.0001"))
            if value is not None
            else None
        )

    return SessaoCaixaDTO(
        id=sessao.id,
        empresa_id=sessao.empresa_id,
        caixa_id=sessao.caixa_id,
        operador_id=sessao.operador_id,
        status=sessao.status,
        data_abertura=sessao.data_abertura,
        saldo_abertura=_dec(sessao.saldo_abertura),
        data_fechamento=sessao.data_fechamento,
        operador_fechamento_id=sessao.operador_fechamento_id,
        saldo_informado_fechamento=_dec_opt(sessao.saldo_informado_fechamento),
        saldo_sistema_fechamento=_dec_opt(sessao.saldo_sistema_fechamento),
        diferenca_fechamento=_dec_opt(sessao.diferenca_fechamento),
        total_vendas_bruto=_dec(sessao.total_vendas_bruto),
        total_descontos=_dec(sessao.total_descontos),
        total_liquido=_dec(sessao.total_liquido),
        total_dinheiro=_dec(sessao.total_dinheiro),
        total_pix=_dec(sessao.total_pix),
        total_cartao_debito=_dec(sessao.total_cartao_debito),
        total_cartao_credito=_dec(sessao.total_cartao_credito),
        total_outros=_dec(sessao.total_outros),
        quantidade_vendas=int(sessao.quantidade_vendas or 0),
        ticket_medio=_dec_opt(sessao.ticket_medio),
        observacao_fechamento=sessao.observacao_fechamento,
    )


class AbrirSessaoUseCase:
    def __init__(self, repo: CaixaRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        request: AbrirSessaoRequest,
        empresa_id: UUID,
        operador_id: UUID,
    ) -> SessaoCaixaDTO:
        caixa = await self._repo.get_caixa(request.caixa_id, empresa_id)
        if not caixa:
            raise NotFoundError("Caixa não encontrado.")

        sessao_existente = await self._repo.get_sessao_ativa(request.caixa_id, empresa_id)
        if sessao_existente:
            raise ConflictError("Caixa já possui uma sessão aberta.")

        sessao = SessaoCaixa(
            empresa_id=empresa_id,
            caixa_id=request.caixa_id,
            operador_id=operador_id,
            status=StatusSessaoCaixa.ABERTA,
            data_abertura=datetime.now(timezone.utc),
            saldo_abertura=request.saldo_abertura,
            total_vendas_bruto=0,
            total_cancelamentos=0,
            total_descontos=0,
            total_liquido=0,
            total_sangrias=0,
            total_suprimentos=0,
            total_dinheiro=0,
            total_pix=0,
            total_cartao_debito=0,
            total_cartao_credito=0,
            total_outros=0,
            quantidade_vendas=0,
        )
        sessao = await self._repo.save(sessao)
        return _to_dto(sessao)


class GetSessaoAtivaUseCase:
    def __init__(self, repo: CaixaRepository) -> None:
        self._repo = repo

    async def execute(self, caixa_id: UUID, empresa_id: UUID) -> SessaoCaixaDTO:
        sessao = await self._repo.get_sessao_ativa(caixa_id, empresa_id)
        if not sessao:
            raise NotFoundError("Nenhuma sessão aberta para este caixa.")
        return _to_dto(sessao)


class FecharSessaoUseCase:
    def __init__(self, repo: CaixaRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        sessao_id: UUID,
        request: FecharSessaoRequest,
        empresa_id: UUID,
        operador_fechamento_id: UUID,
    ) -> SessaoCaixaDTO:
        sessao = await self._repo.get_sessao_by_id(sessao_id, empresa_id)
        if not sessao:
            raise NotFoundError("Sessão não encontrada.")
        if sessao.status != StatusSessaoCaixa.ABERTA:
            raise BusinessRuleError("Sessão já está fechada.")

        totais = await self._repo.calcular_totais_sessao(sessao_id)

        total_liquido = totais["total_liquido"]
        saldo_sistema = (
            float(sessao.saldo_abertura)
            + totais["total_dinheiro"]
            + float(sessao.total_suprimentos or 0)
            - float(sessao.total_sangrias or 0)
        )
        saldo_informado = float(request.saldo_informado_fechamento)

        sessao.status = StatusSessaoCaixa.FECHADA
        sessao.data_fechamento = datetime.now(timezone.utc)
        sessao.operador_fechamento_id = operador_fechamento_id
        sessao.saldo_informado_fechamento = saldo_informado
        sessao.saldo_sistema_fechamento = saldo_sistema
        sessao.diferenca_fechamento = saldo_informado - saldo_sistema
        sessao.total_vendas_bruto = totais["total_vendas_bruto"]
        sessao.total_descontos = totais["total_descontos"]
        sessao.total_liquido = total_liquido
        sessao.total_dinheiro = totais["total_dinheiro"]
        sessao.total_pix = totais["total_pix"]
        sessao.total_cartao_debito = totais["total_cartao_debito"]
        sessao.total_cartao_credito = totais["total_cartao_credito"]
        sessao.total_outros = totais["total_outros"]
        sessao.quantidade_vendas = totais["quantidade_vendas"]
        if totais["quantidade_vendas"] > 0:
            sessao.ticket_medio = total_liquido / totais["quantidade_vendas"]
        sessao.observacao_fechamento = request.observacao

        await self._repo._session.flush()
        return _to_dto(sessao)
