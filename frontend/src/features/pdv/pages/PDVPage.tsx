import { useEffect, useCallback } from 'react'
import { Plus, CreditCard, ShoppingBag, LogOut } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'

import { usePDVStore } from '@/store/pdvStore'
import { useAuthStore } from '@/store/authStore'
import { useConnectivity } from '@/hooks/useConnectivity'
import { usePDV } from '../hooks/usePDV'

import { StatusBarPDV } from '../components/StatusBarPDV'
import { BarcodeInput } from '../components/BarcodeInput'
import { VendaItemList } from '../components/VendaItemList'
import { VendaResumo } from '../components/VendaResumo'
import { PagamentoPanel } from '../components/PagamentoPanel'
import { ModalRemocaoItem } from '../components/ModalRemocaoItem'
import { OfflineBanner } from '../components/OfflineBanner'
import { SyncStatusIndicator } from '../components/SyncStatusIndicator'
export function PDVPage() {
  const navigate = useNavigate()
  const {
    sessaoCaixa,
    vendaAtual,
    ultimoProduto,
    itemSelecionadoId,
    painelPagamentoAberto,
    modalRemocaoAberto,
    flash,
    isOffline,
    modoEmissaoSelecionado,
    scannerPodeFocar,
    setItemSelecionadoId,
    setModoEmissaoSelecionado,
    setPainelPagamentoAberto,
    setModalRemocaoAberto,
  } = usePDVStore()

  const { clearSession } = useAuthStore()
  // Registra o detector de conectividade (uma vez por montagem da página)
  useConnectivity()
  const { loadingBarcode, loadingAcao, novaVenda, ensureVendaAberta, lerBarcode, removerItemVenda, registrarPagamento, finalizarVenda, selecionarModoEmissao, setScannerPodeFocar } =
    usePDV()

  // Redireciona se não há sessão de caixa
  useEffect(() => {
    if (!sessaoCaixa) navigate('/caixa')
  }, [sessaoCaixa, navigate])

  useEffect(() => {
    if (!sessaoCaixa) return
    if (!vendaAtual || vendaAtual.status !== 'em_aberto') {
      void ensureVendaAberta()
    }
  }, [ensureVendaAberta, sessaoCaixa, vendaAtual])

  // ----- Atalhos de teclado globais -----
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const target = e.target as HTMLElement
      const isEditable =
        target.isContentEditable ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT'

      if ((e.ctrlKey || e.metaKey || e.altKey) && isEditable) {
        return
      }

      // F2 → Finalizar como GERENCIAL (Pedido / Orçamento)
      if (e.key === 'F2') {
        e.preventDefault()
        setModoEmissaoSelecionado('GERENCIAL')
        if (!loadingAcao && vendaAtual) void finalizarVenda('GERENCIAL')
        return
      }
      // F4 → Finalizar como FISCAL (NFC-e)
      if (e.key === 'F4') {
        e.preventDefault()
        setModoEmissaoSelecionado('FISCAL')
        if (!loadingAcao && vendaAtual) void finalizarVenda('FISCAL')
        return
      }
      // F6 → Nova Venda manual
      if (e.key === 'F6') {
        e.preventDefault()
        if (!loadingAcao) novaVenda()
        return
      }
      // F8 → Remover item selecionado
      if (e.key === 'F8') {
        e.preventDefault()
        if (itemSelecionadoId) setModalRemocaoAberto(true)
        return
      }
      // Esc → Fechar painéis
      if (e.key === 'Escape') {
        if (modalRemocaoAberto) { setModalRemocaoAberto(false); return }
        if (painelPagamentoAberto) { setPainelPagamentoAberto(false); return }
        setItemSelecionadoId(null)
        return
      }
    },
    [
      finalizarVenda,
      novaVenda,
      loadingAcao,
      vendaAtual,
      itemSelecionadoId,
      painelPagamentoAberto,
      modalRemocaoAberto,
      setItemSelecionadoId,
      setModoEmissaoSelecionado,
      setPainelPagamentoAberto,
      setModalRemocaoAberto,
    ],
  )

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  const itensAtivos = vendaAtual?.itens.filter((i) => !i.cancelado) ?? []
  const totalPago = vendaAtual?.pagamentos.reduce((s, p) => s + parseFloat(p.valor), 0) ?? 0
  const itemSelecionado = vendaAtual?.itens.find((i) => i.id === itemSelecionadoId) ?? null

  return (
    <div className="flex h-screen flex-col bg-pdv-bg overflow-hidden">
      {/* Barra de status */}
      <StatusBarPDV sessao={sessaoCaixa} venda={vendaAtual ?? null} modoEmissao={modoEmissaoSelecionado} />

      {/* Banner de modo offline */}
      {isOffline && <OfflineBanner />}

      {/* Flash notification */}
      {flash && (
        <div
          className={clsx(
            'fixed right-4 top-12 z-40 max-w-xs rounded-xl border px-4 py-3 text-sm font-medium shadow-xl',
            'animate-slide-in',
            flash.type === 'success' && 'border-emerald-700/40 bg-emerald-500/10 text-emerald-300',
            flash.type === 'error' && 'border-red-700/40 bg-red-500/10 text-red-300',
            flash.type === 'info' && 'border-blue-700/40 bg-blue-500/10 text-blue-300',
          )}
        >
          {flash.message}
        </div>
      )}

      {/* Área principal */}
      <div className="flex flex-1 overflow-hidden">
        {/* ── COLUNA ESQUERDA: Barcode + Itens ── */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Barcode input */}
          <div className="border-b border-pdv-border bg-pdv-surface px-4 pt-4 pb-5">
            <BarcodeInput
              onScan={lerBarcode}
              loading={loadingBarcode}
              disabled={vendaAtual?.status === 'concluida'}
              autoFocusEnabled={scannerPodeFocar && !!vendaAtual && vendaAtual.status === 'em_aberto'}
              lastProduct={ultimoProduto?.produto.descricao_pdv ?? ultimoProduto?.produto.descricao}
            />
          </div>

          {/* Toolbar */}
          <div className="flex items-center gap-2 border-b border-pdv-border bg-pdv-surface/60 px-4 py-2">
            <button
              onClick={() => void novaVenda()}
              disabled={loadingAcao && !vendaAtual}
              className="flex items-center gap-1.5 rounded-lg border border-pdv-border bg-pdv-surface px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-pdv-surface-2 hover:text-slate-100 transition-colors disabled:opacity-50"
            >
              <Plus size={13} />
              Nova Venda
              <kbd className="rounded border border-pdv-border bg-pdv-bg px-1 font-mono text-[10px] text-slate-600">F6</kbd>
            </button>

            {itemSelecionadoId && (
              <button
                onClick={() => setModalRemocaoAberto(true)}
                className="flex items-center gap-1.5 rounded-lg border border-red-700/40 bg-red-500/10 px-3 py-1.5 text-xs font-medium text-red-400 hover:bg-red-500/20 transition-colors"
              >
                Remover Item
                <kbd className="rounded border border-red-800/40 bg-pdv-bg px-1 font-mono text-[10px] text-red-700">F8</kbd>
              </button>
            )}

            <div className="flex-1" />

            {/* Indicador de sync pendente */}
            <SyncStatusIndicator />

            {vendaAtual && (
              <span className="text-xs text-slate-600">
                {itensAtivos.length} {itensAtivos.length === 1 ? 'item' : 'itens'}
              </span>
            )}
          </div>

          {/* Lista de itens */}
          <div className="flex flex-1 flex-col overflow-auto">
            {vendaAtual ? (
              <VendaItemList
                itens={vendaAtual.itens}
                itemSelecionadoId={itemSelecionadoId}
                onSelectItem={setItemSelecionadoId}
                onRemoveItem={(id) => {
                  setItemSelecionadoId(id)
                  setModalRemocaoAberto(true)
                }}
              />
            ) : (
              <div className="flex flex-1 flex-col items-center justify-center gap-3 py-16 text-slate-700">
                <ShoppingBag size={48} className="opacity-20" />
                <p className="text-sm text-slate-600">Nenhuma venda em andamento</p>
                <p className="text-xs text-slate-700 opacity-70">
                  Leia um produto ou pressione{' '}
                  <kbd className="rounded border border-pdv-border bg-pdv-surface px-1.5 py-0.5 font-mono text-xs text-slate-500">
                    F6
                  </kbd>{' '}
                  para iniciar
                </p>
              </div>
            )}
          </div>
        </div>

        {/* ── COLUNA DIREITA: Resumo + Pagamento ── */}
        <div className="flex w-80 shrink-0 flex-col gap-0 border-l border-pdv-border bg-pdv-surface xl:w-96">
          {/* Header da coluna direita */}
          <div className="flex items-center gap-2 border-b border-pdv-border bg-pdv-surface px-4 py-3">
            <CreditCard size={15} className="text-slate-500" />
            <span className="text-sm font-semibold text-slate-200">Pagamento</span>
            <div className="flex-1" />
            <button
              onClick={() => setPainelPagamentoAberto(!painelPagamentoAberto)}
              className="text-xs text-slate-600 hover:text-slate-400 transition-colors"
            >
              {painelPagamentoAberto ? 'Ocultar' : 'Mostrar'}
            </button>
          </div>

          <div className="flex flex-1 flex-col gap-4 overflow-auto p-4">
            {/* Resumo financeiro da venda */}
            {vendaAtual ? (
              <VendaResumo
                venda={vendaAtual}
                totalPago={totalPago}
                modoEmissaoSelecionado={modoEmissaoSelecionado}
              />
            ) : (
              <div className="rounded-xl border border-pdv-border bg-pdv-surface/50 p-4 text-center text-sm text-slate-600">
                Sem venda ativa
              </div>
            )}

            {/* Painel de pagamento */}
            {vendaAtual && (
              <PagamentoPanel
                venda={vendaAtual}
                totalPago={totalPago}
                onPagar={registrarPagamento}
                modoEmissaoSelecionado={modoEmissaoSelecionado}
                onSelecionarModoEmissao={selecionarModoEmissao}
                onFinalizarFiscal={() => finalizarVenda('FISCAL')}
                onFinalizarGerencial={() => finalizarVenda('GERENCIAL')}
                onScannerFocusChange={setScannerPodeFocar}
                loadingFinalizar={loadingAcao}
              />
            )}

            {/* Botão logout / fechar caixa */}
            <div className="mt-auto pt-2 border-t border-pdv-border/40">
              <button
                onClick={() => { clearSession(); navigate('/login') }}
                className="flex w-full items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs text-slate-600 hover:bg-pdv-surface-2 hover:text-slate-400 transition-colors"
              >
                <LogOut size={12} />
                Sair do sistema
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ── BARRA INFERIOR: Atalhos ── */}
      <ShortcutsBar />

      {/* ── MODAL de remoção ── */}
      <ModalRemocaoItem
        open={modalRemocaoAberto}
        item={itemSelecionado}
        onConfirm={async () => {
          if (itemSelecionadoId) {
            await removerItemVenda(itemSelecionadoId)
            setModalRemocaoAberto(false)
          }
        }}
        onCancel={() => setModalRemocaoAberto(false)}
        loading={loadingAcao}
      />
    </div>
  )
}

// Barra inferior com hints de atalhos
function ShortcutsBar({ minimal = false }: { minimal?: boolean }) {
  const shortcuts = minimal
    ? [{ kbd: 'F4', label: 'Venda Fiscal' }]
    : [
        { kbd: 'F2', label: 'Pedido / Gerencial' },
        { kbd: 'F4', label: 'Venda Fiscal' },
        { kbd: 'F6', label: 'Nova Venda' },
        { kbd: 'F8', label: 'Remover Item' },
        { kbd: 'Esc', label: 'Cancelar' },
      ]

  return (
    <div className="flex items-center gap-4 border-t border-pdv-border bg-pdv-bg px-4 py-1.5">
      {shortcuts.map((s) => (
        <div key={s.kbd} className="flex items-center gap-1.5 text-xs">
          <kbd className="rounded border border-pdv-border bg-pdv-surface px-1.5 py-0.5 font-mono text-slate-500">
            {s.kbd}
          </kbd>
          <span className="text-slate-600">{s.label}</span>
        </div>
      ))}
    </div>
  )
}
