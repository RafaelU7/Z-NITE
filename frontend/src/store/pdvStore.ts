import { create } from 'zustand'
import type { SessaoCaixaDTO, VendaDTO, ProdutoDTO, TipoEmissao } from '@/shared/types/api'

// Estado inicializado a partir da conectividade real do navegador
const initialIsOffline = typeof navigator !== 'undefined' ? !navigator.onLine : false

// Estado do último produto lido — para feedback visual
export interface UltimoProdutoLido {
  produto: ProdutoDTO
  timestamp: number
}

type FlashType = 'success' | 'error' | 'info' | null

interface PDVState {
  // Sessão de caixa ativa
  sessaoCaixa: SessaoCaixaDTO | null
  setSessaoCaixa: (s: SessaoCaixaDTO | null) => void

  // Venda em andamento
  vendaAtual: VendaDTO | null
  setVendaAtual: (v: VendaDTO | null) => void

  // Produto lido no barcode (feedback)
  ultimoProduto: UltimoProdutoLido | null
  setUltimoProduto: (p: ProdutoDTO | null) => void

  // Item selecionado na lista (para remoção via F8)
  itemSelecionadoId: string | null
  setItemSelecionadoId: (id: string | null) => void

  // Painel de pagamento aberto
  painelPagamentoAberto: boolean
  setPainelPagamentoAberto: (open: boolean) => void

  // Modo escolhido para finalização da venda atual
  modoEmissaoSelecionado: TipoEmissao
  setModoEmissaoSelecionado: (modo: TipoEmissao) => void

  // Controle de foco do scanner para não atrapalhar inputs críticos
  scannerPodeFocar: boolean
  setScannerPodeFocar: (enabled: boolean) => void

  // Feedback visual flash
  flash: { type: FlashType; message: string } | null
  setFlash: (f: { type: FlashType; message: string } | null) => void

  // Modal de remoção
  modalRemocaoAberto: boolean
  setModalRemocaoAberto: (open: boolean) => void

  // Venda finalizada (para tela de confirmação)
  vendaFinalizada: VendaDTO | null
  setVendaFinalizada: (v: VendaDTO | null) => void

  // --- Offline ---
  isOffline: boolean
  setIsOffline: (b: boolean) => void

  pendentesSync: number
  setPendentesSync: (n: number) => void

  syncEmAndamento: boolean
  setSyncEmAndamento: (b: boolean) => void

  ultimoSyncErro: string | null
  setUltimoSyncErro: (e: string | null) => void
}

export const usePDVStore = create<PDVState>()((set) => ({
  sessaoCaixa: null,
  setSessaoCaixa: (s) => set({ sessaoCaixa: s }),

  vendaAtual: null,
  setVendaAtual: (v) => set({ vendaAtual: v }),

  ultimoProduto: null,
  setUltimoProduto: (p) =>
    set({ ultimoProduto: p ? { produto: p, timestamp: Date.now() } : null }),

  itemSelecionadoId: null,
  setItemSelecionadoId: (id) => set({ itemSelecionadoId: id }),

  painelPagamentoAberto: false,
  setPainelPagamentoAberto: (open) => set({ painelPagamentoAberto: open }),

  modoEmissaoSelecionado: 'FISCAL',
  setModoEmissaoSelecionado: (modo) => set({ modoEmissaoSelecionado: modo }),

  scannerPodeFocar: true,
  setScannerPodeFocar: (enabled) => set({ scannerPodeFocar: enabled }),

  flash: null,
  setFlash: (f) => set({ flash: f }),

  modalRemocaoAberto: false,
  setModalRemocaoAberto: (open) => set({ modalRemocaoAberto: open }),

  vendaFinalizada: null,
  setVendaFinalizada: (v) => set({ vendaFinalizada: v }),

  isOffline: initialIsOffline,
  setIsOffline: (b) => set({ isOffline: b }),

  pendentesSync: 0,
  setPendentesSync: (n) => set({ pendentesSync: n }),

  syncEmAndamento: false,
  setSyncEmAndamento: (b) => set({ syncEmAndamento: b }),

  ultimoSyncErro: null,
  setUltimoSyncErro: (e) => set({ ultimoSyncErro: e }),
}))
