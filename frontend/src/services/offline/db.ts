/**
 * IndexedDB — banco local para suporte offline do PDV Zênite.
 *
 * Stores:
 *   vendas_offline    — vendas pendentes de sincronização
 *   catalogo_produtos — cache de produtos para busca sem internet
 *   contador_local    — sequências locais (numero_venda_local por sessão)
 */

import { openDB, type IDBPDatabase } from 'idb'
import type { VendaOffline, ProdutoCatalogOffline } from './types'

const DB_NAME = 'zenite-pdv-offline'
const DB_VERSION = 1

interface ZeniteOfflineDB {
  vendas_offline: {
    key: string
    value: VendaOffline
    indexes: {
      'by-status': string
      'by-sessao': string
    }
  }
  catalogo_produtos: {
    key: string
    value: ProdutoCatalogOffline
    indexes: {
      'by-ean': string
    }
  }
  contador_local: {
    key: string
    value: { id: string; valor: number }
  }
}

let dbPromise: Promise<IDBPDatabase<ZeniteOfflineDB>> | null = null

export function getDB(): Promise<IDBPDatabase<ZeniteOfflineDB>> {
  if (!dbPromise) {
    dbPromise = openDB<ZeniteOfflineDB>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains('vendas_offline')) {
          const store = db.createObjectStore('vendas_offline', {
            keyPath: 'venda_id',
          })
          store.createIndex('by-status', 'status_local')
          store.createIndex('by-sessao', 'sessao_caixa_id')
        }

        if (!db.objectStoreNames.contains('catalogo_produtos')) {
          const store = db.createObjectStore('catalogo_produtos', {
            keyPath: 'id',
          })
          store.createIndex('by-ean', 'codigo_barras_principal')
        }

        if (!db.objectStoreNames.contains('contador_local')) {
          db.createObjectStore('contador_local', { keyPath: 'id' })
        }
      },
    })
  }
  return dbPromise
}
