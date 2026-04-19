/**
 * Serviço de sincronização — envia lotes de vendas offline para o backend.
 *
 * Fluxo:
 *   1. Busca todas as vendas com status pendente_sync
 *   2. Marca todas como sincronizando (para evitar duplo envio)
 *   3. Envia lote para POST /v1/sync/vendas
 *   4. Processa resultado: aceitas → sincronizada, duplicadas → sincronizada,
 *      rejeitadas → erro_sync
 *   5. Em caso de erro de rede: reverte para pendente_sync (próximo ciclo tenta)
 */

import api from '@/services/api/client'
import type { VendaOffline } from './types'
import type { FormaPagamento } from '@/shared/types/api'
import {
  getVendasPendentesSync,
  marcarSincronizando,
  marcarSincronizada,
  marcarErroSync,
  countVendasPendentes,
} from './vendaOfflineService'

// ---------------------------------------------------------------------------
// Tipos da API de sync
// ---------------------------------------------------------------------------

interface SyncResultAceita {
  chave_idempotencia: string
  venda_id: string
}

interface SyncResultDuplicada {
  chave_idempotencia: string
  venda_id: string
}

interface SyncResultRejeitada {
  chave_idempotencia: string
  motivo: string
}

interface SyncBatchResponse {
  aceitas: SyncResultAceita[]
  duplicadas: SyncResultDuplicada[]
  rejeitadas: SyncResultRejeitada[]
}

export interface SyncResultado {
  sucesso: number
  duplicadas: number
  erros: number
}

const FORMA_PAGAMENTO_SYNC_MAP: Record<FormaPagamento, string> = {
  '01': '01',
  '03': '03',
  '04': '04',
  '17': '17',
  '99': '99',
}

// ---------------------------------------------------------------------------
// Construção do payload
// ---------------------------------------------------------------------------

function buildVendaPayload(venda: VendaOffline) {
  return {
    chave_idempotencia: venda.chave_idempotencia,
    sessao_caixa_id: venda.sessao_caixa_id,
    origem_pdv: venda.origem_pdv,
    data_venda: venda.data_venda,
    tipo_emissao: venda.tipo_emissao ?? 'FISCAL',
    itens: venda.itens
      .filter((i) => !i.cancelado)
      .map((i) => ({
        produto_id: i.produto_id,
        descricao_produto: i.descricao_produto,
        codigo_barras: i.codigo_barras,
        unidade: i.unidade,
        sequencia: i.sequencia,
        quantidade: i.quantidade.toFixed(3),
        preco_unitario: i.preco_unitario.toFixed(4),
        desconto_unitario: i.desconto_unitario.toFixed(4),
        snapshot_fiscal: i.snapshot_fiscal,
      })),
    pagamentos: venda.pagamentos.map((p) => ({
      forma_pagamento: FORMA_PAGAMENTO_SYNC_MAP[p.forma_pagamento],
      valor: p.valor.toFixed(2),
      troco: p.troco.toFixed(2),
      nsu: p.nsu,
      bandeira_cartao: p.bandeira_cartao,
    })),
  }
}

// ---------------------------------------------------------------------------
// Execução do sync
// ---------------------------------------------------------------------------

let syncEmAndamento = false

export async function executarSyncPendentes(): Promise<SyncResultado> {
  if (syncEmAndamento) return { sucesso: 0, duplicadas: 0, erros: 0 }

  const pendentes = await getVendasPendentesSync()
  if (pendentes.length === 0) return { sucesso: 0, duplicadas: 0, erros: 0 }

  syncEmAndamento = true

  try {
    // 1. Marca todas como "sincronizando" para evitar duplo envio
    await marcarSincronizando(pendentes.map((v) => v.venda_id))

    // 2. Envia lote para o backend
    const { data } = await api.post<SyncBatchResponse>('/sync/vendas', {
      vendas: pendentes.map(buildVendaPayload),
    })

    // 3. Mapa: chave_idempotencia → venda_id local
    const byChave = new Map(
      pendentes.map((v) => [v.chave_idempotencia, v.venda_id]),
    )

    // 4. Processar aceitas
    for (const aceita of data.aceitas) {
      const id = byChave.get(aceita.chave_idempotencia)
      if (id) await marcarSincronizada(id)
    }

    // 5. Processar duplicadas (já estão no backend — marca como sincronizada)
    for (const dup of data.duplicadas) {
      const id = byChave.get(dup.chave_idempotencia)
      if (id) await marcarSincronizada(id)
    }

    // 6. Processar rejeitadas
    for (const rej of data.rejeitadas) {
      const id = byChave.get(rej.chave_idempotencia)
      if (id) await marcarErroSync(id, rej.motivo ?? 'Rejeitada pelo servidor.')
    }

    return {
      sucesso: data.aceitas.length,
      duplicadas: data.duplicadas.length,
      erros: data.rejeitadas.length,
    }
  } catch (err) {
    // Erro de rede: marca todas como erro para nova tentativa
    for (const venda of pendentes) {
      await marcarErroSync(
        venda.venda_id,
        err instanceof Error ? err.message : 'Erro de conexão ao sincronizar.',
      )
    }
    throw err
  } finally {
    syncEmAndamento = false
  }
}

/** Retorna o número de vendas que ainda precisam ser sincronizadas. */
export { countVendasPendentes }
