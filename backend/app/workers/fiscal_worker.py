"""
ARQ Worker — processamento assíncrono de documentos fiscais.

Startup:
  arq app.workers.fiscal_worker.WorkerSettings

O contexto `ctx` disponível em cada job inclui:
  - ctx['redis']: ArqRedis pool (auto-injetado pelo ARQ)
  - ctx['db_session_factory']: async_sessionmaker criado no startup

Referência: https://arq-docs.helpmanual.io/
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.infrastructure.database.models.empresa import Empresa
from app.infrastructure.database.models.enums import StatusDocumentoFiscal
from app.infrastructure.database.models.fiscal import DocumentoFiscal
from app.infrastructure.database.models.numeracao_fiscal import SequenciaFiscal
from app.infrastructure.database.models.venda import Venda
from app.infrastructure.fiscal.focus_nfe import FocusNFeGateway
from app.infrastructure.fiscal.gateway import FiscalGateway
from app.infrastructure.fiscal.mock_gateway import MockFiscalGateway
from app.infrastructure.fiscal.payload_builder import (
    build_nfce_payload,
    payload_to_audit_string,
)

log = logging.getLogger(__name__)


def _get_gateway(settings) -> FiscalGateway:
    """Retorna o gateway correto conforme configuração."""
    if settings.focus_nfe_token:
        return FocusNFeGateway(
            token=settings.focus_nfe_token,
            base_url=settings.focus_nfe_base_url,
            timeout=settings.focus_nfe_timeout,
        )
    log.warning("FOCUS_NFE_TOKEN não configurado — usando MockFiscalGateway")
    return MockFiscalGateway()


# ---------------------------------------------------------------------------
# Job principal
# ---------------------------------------------------------------------------


async def processar_documento_fiscal(ctx: dict, documento_id: str) -> None:
    """
    Emite um DocumentoFiscal via FiscalGateway.

    Fluxo:
      1. Carrega o documento com SELECT FOR UPDATE (exclusão de concorrência)
      2. Verifica se ainda precisa ser processado
      3. Carrega venda + empresa
      4. Monta payload e envia ao provedor
      5. Atualiza o documento com o resultado
      6. Em caso de erro técnico: re-enfileira com backoff exponencial
    """
    settings = get_settings()
    doc_uuid = UUID(documento_id)
    session_factory: async_sessionmaker[AsyncSession] = ctx["db_session_factory"]

    async with session_factory() as session:
        async with session.begin():
            # 1. Carrega com FOR UPDATE (skip_locked → outro worker pode pegar se já bloqueado)
            result = await session.execute(
                select(DocumentoFiscal)
                .where(DocumentoFiscal.id == doc_uuid)
                .with_for_update(skip_locked=True)
            )
            doc = result.scalar_one_or_none()

            if doc is None:
                log.info("Documento %s não encontrado ou já bloqueado — ignorando", documento_id)
                return

            # 2. Verifica se ainda deve processar
            if doc.status not in (
                StatusDocumentoFiscal.PENDENTE,
                StatusDocumentoFiscal.ERRO,
            ):
                log.info(
                    "Documento %s com status=%s — nada a fazer",
                    documento_id,
                    doc.status,
                )
                return

            if doc.tentativas >= settings.fiscal_max_tentativas:
                log.warning(
                    "Documento %s esgotou %d tentativas", documento_id, doc.tentativas
                )
                doc.status = StatusDocumentoFiscal.ERRO
                doc.mensagem_retorno = (
                    f"Máximo de {settings.fiscal_max_tentativas} tentativas atingido"
                )
                return

            # 3. Carrega venda com relationships e empresa
            if doc.venda_id is None:
                doc.status = StatusDocumentoFiscal.ERRO
                doc.mensagem_retorno = "Documento sem venda associada"
                return

            venda_result = await session.execute(
                select(Venda)
                .where(Venda.id == doc.venda_id)
                .options(
                    selectinload(Venda.itens),
                    selectinload(Venda.pagamentos),
                )
            )
            venda = venda_result.scalar_one_or_none()

            if venda is None:
                doc.status = StatusDocumentoFiscal.ERRO
                doc.mensagem_retorno = "Venda não encontrada"
                return

            empresa_result = await session.execute(
                select(Empresa).where(Empresa.id == doc.empresa_id)
            )
            empresa = empresa_result.scalar_one_or_none()

            if empresa is None:
                doc.status = StatusDocumentoFiscal.ERRO
                doc.mensagem_retorno = "Empresa não encontrada"
                return

            # 4. Obtém numeração — SELECT FOR UPDATE na SequenciaFiscal
            serie = empresa.serie_nfce or 1
            seq_result = await session.execute(
                select(SequenciaFiscal)
                .where(SequenciaFiscal.empresa_id == doc.empresa_id)
                .where(SequenciaFiscal.tipo == "nfce")
                .where(SequenciaFiscal.serie == serie)
                .with_for_update()
            )
            seq = seq_result.scalar_one_or_none()

            numero: int
            if seq is None:
                # Cria a sequência na primeira emissão
                seq = SequenciaFiscal(
                    empresa_id=doc.empresa_id,
                    tipo="nfce",
                    serie=serie,
                    proximo_numero=1,
                )
                session.add(seq)
                await session.flush()
                numero = 1
            else:
                numero = seq.proximo_numero

            seq.proximo_numero = numero + 1
            await session.flush()

            # 5. Monta payload e envia
            payload = build_nfce_payload(
                venda=venda,
                empresa=empresa,
                numero=numero,
                serie=serie,
            )

            gateway = _get_gateway(settings)
            ref = str(doc.id)

            log.info("Emitindo NFC-e — ref=%s tentativa=%d", ref, doc.tentativas + 1)
            resultado = await gateway.emitir_nfce(ref=ref, payload=payload)

            # 6. Atualiza documento com o resultado
            doc.tentativas += 1
            doc.xml_enviado = payload_to_audit_string(payload)
            doc.data_emissao = venda.data_venda

            if resultado.status == "emitida":
                doc.status = StatusDocumentoFiscal.EMITIDA
                doc.chave_acesso = resultado.chave_acesso
                doc.numero = resultado.numero or numero
                doc.serie = resultado.serie or serie
                doc.data_autorizacao = resultado.data_autorizacao
                doc.protocolo_autorizacao = resultado.protocolo_autorizacao
                doc.xml_retorno = resultado.xml_retorno
                doc.url_danfe = resultado.url_danfe
                doc.url_qrcode = resultado.url_qrcode
                doc.url_consulta_nfe = resultado.url_consulta_nfe
                doc.codigo_retorno = resultado.codigo_retorno
                doc.mensagem_retorno = resultado.mensagem_retorno
                doc.provider_id = resultado.provider_id
                doc.provider_metadata = resultado.provider_metadata
                log.info(
                    "NFC-e emitida — chave=%s protocolo=%s",
                    doc.chave_acesso,
                    doc.protocolo_autorizacao,
                )

            elif resultado.is_rejection:
                # Rejeição pela SEFAZ — não faz retry
                doc.status = StatusDocumentoFiscal.REJEITADA
                doc.codigo_retorno = resultado.codigo_retorno
                doc.mensagem_retorno = resultado.mensagem_retorno
                doc.provider_metadata = resultado.provider_metadata
                log.warning(
                    "NFC-e rejeitada — cStat=%s motivo=%s",
                    resultado.codigo_retorno,
                    resultado.mensagem_retorno,
                )

            elif resultado.status == "pendente":
                # Focus NFe ainda processando — tenta novamente em 30s
                doc.status = StatusDocumentoFiscal.PENDENTE
                doc.proxima_tentativa_em = datetime.now(timezone.utc) + timedelta(seconds=30)
                arq_redis = ctx["redis"]
                await arq_redis.enqueue_job(
                    "processar_documento_fiscal",
                    documento_id,
                    _job_id=f"fiscal-{documento_id}",
                    _defer_by=30,
                )
                log.info("NFC-e pendente no provedor — re-agendado em 30s")

            else:
                # Erro técnico — re-enfileira com backoff exponencial
                doc.status = StatusDocumentoFiscal.ERRO
                doc.codigo_retorno = resultado.codigo_retorno
                doc.mensagem_retorno = resultado.mensagem_retorno or resultado.error_message
                doc.provider_metadata = resultado.provider_metadata
                log.error(
                    "Erro técnico na emissão — tentativa=%d erro=%s",
                    doc.tentativas,
                    resultado.error_message,
                )

                if doc.tentativas < settings.fiscal_max_tentativas:
                    delay_seconds = min(60 * (2 ** (doc.tentativas - 1)), 3600)
                    retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
                    doc.proxima_tentativa_em = retry_at
                    arq_redis = ctx["redis"]
                    await arq_redis.enqueue_job(
                        "processar_documento_fiscal",
                        documento_id,
                        _job_id=f"fiscal-{documento_id}",
                        _defer_by=delay_seconds,
                    )
                    log.info(
                        "Re-agendado em %ds (tentativa %d/%d)",
                        delay_seconds,
                        doc.tentativas,
                        settings.fiscal_max_tentativas,
                    )


# ---------------------------------------------------------------------------
# Lifecycle hooks
# ---------------------------------------------------------------------------


async def startup(ctx: dict) -> None:
    """Inicializa pool de conexões DB para o worker."""
    settings = get_settings()
    engine = create_async_engine(
        settings.async_database_url,
        pool_size=3,
        max_overflow=5,
        pool_pre_ping=True,
    )
    ctx["db_engine"] = engine
    ctx["db_session_factory"] = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    log.info("FiscalWorker: conexão DB inicializada")


async def shutdown(ctx: dict) -> None:
    """Fecha pool de conexões DB."""
    engine = ctx.get("db_engine")
    if engine:
        await engine.dispose()
    log.info("FiscalWorker: conexão DB encerrada")


# ---------------------------------------------------------------------------
# Worker settings
# ---------------------------------------------------------------------------


class WorkerSettings:
    """
    Configuração do worker ARQ.
    Para iniciar: arq app.workers.fiscal_worker.WorkerSettings
    """
    functions = [processar_documento_fiscal]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    queue_name = "arq:zenite_fiscal"
    max_jobs = 4
    job_timeout = 120  # segundos por job
    poll_delay = 0.5
    keep_result = 3600  # mantém resultado 1h para debugging
